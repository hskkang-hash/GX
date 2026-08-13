import json
from core.base import BooleanField
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Min, Max, F, Case, When, Value, CharField, OuterRef, Subquery, Prefetch, Exists, Q
from django.contrib.contenttypes.models import ContentType

from django.db.models.expressions import RawSQL
from terminals.models import Routes, RouteTerminal, Terminal, TerminalType
from devices.models import Measurement
from common.constant import MESSAGE_ENUM


class RoutesService:
    @transaction.atomic
    def create_route(self, data):
        """
        Create a new route with associated terminals
        
        Args:
            data: RouteCreateSchema data
            
        Returns:
            tuple: (success, result)
        """
        try:
            # Validate that at least one terminal is provided
            if not data.get('terminals') or len(data.get('terminals')) == 0:
                return False, "At least one terminal must be associated with the route"
            
            # Extract route data
            route_data = data
            terminals_data = route_data.pop('terminals')
            
            # Create the route
            route = Routes.objects.create(**{k: v for k, v in route_data.items() if k != 'total_distance' and k != 'estimated_time'})
            
            # Set measurements if provided
            if route_data.get('total_distance'):
                route.set_measurement('total_distance', route_data.get('total_distance'))
                
            if route_data.get('estimated_time'):
                route.set_measurement('estimated_time', route_data.get('estimated_time'))
            
            # Add terminal associations
            self._create_route_terminals(route, terminals_data)
            
            return True, route
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def _create_route_terminals(self, route, terminals_data):
        """
        Create route terminal associations
        
        Args:
            route: Routes instance
            terminals_data: List of RouteTerminalInSchema data
        """
        def _maybe_json(value):
            if value and isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return value

        def _parse_simple_value_to_data(value, default_unit: str, context: str = None):
            """
            Build Measurement.data for 'simple' type without hitting DB.
            Accepts numeric, dict, or string (e.g. '10 mins', '5 m/s').
            """
            from decimal import Decimal
            from devices.utils import standardize_unit

            if value is None:
                return None
            if isinstance(value, dict) and value.get('type'):
                return value
            if isinstance(value, (int, float, Decimal)):
                unit = standardize_unit(default_unit, context=context) if default_unit else default_unit
                return {'type': 'simple', 'value': float(value), 'unit': unit}

            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return None
                import re
                m = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/\.]+)?', text)
                if not m:
                    return None
                num = m.group(1).replace(',', '')
                unit = (m.group(2) or default_unit or '').strip()
                unit = standardize_unit(unit, context=context) if unit else unit
                try:
                    return {'type': 'simple', 'value': float(num), 'unit': unit}
                except Exception:
                    return None

            # Fallback: stringify and try again
            return _parse_simple_value_to_data(str(value), default_unit, context=context)

        ct_route_terminal = ContentType.objects.get_for_model(RouteTerminal)

        if not terminals_data:
            return

        # 🚀 DELTA UPDATE by `order` to avoid delete+recreate 300 rows every update
        incoming_orders = []
        for td in terminals_data:
            if td.get('order') is None:
                raise ValidationError("order is required for each terminal in route")
            incoming_orders.append(td.get('order'))

        if len(set(incoming_orders)) != len(incoming_orders):
            raise ValidationError("Duplicate 'order' values in terminals data")

        # Load fields needed for change detection (avoid updating all rows if payload unchanged)
        existing_rts = list(
            RouteTerminal.objects.filter(route=route).only(
                'id', 'order', 'terminal_id', 'stop', 'for_robot', 'command_line', 'frame'
            )
        )
        existing_by_order = {rt.order: rt for rt in existing_rts}
        existing_orders = set(existing_by_order.keys())
        incoming_orders_set = set(incoming_orders)

        # Delete removed orders + cleanup their measurements (GenericFK won't cascade)
        orders_to_delete = existing_orders - incoming_orders_set
        if orders_to_delete:
            rts_to_delete_qs = RouteTerminal.objects.filter(route=route, order__in=list(orders_to_delete))
            Measurement.objects.filter(
                content_type=ct_route_terminal,
                object_id__in=rts_to_delete_qs.values_list('id', flat=True),
            ).delete()
            rts_to_delete_qs.delete()

        # 1) Load existing terminals in one query
        terminal_ids = [td.get('terminal_id') for td in terminals_data if td.get('terminal_id')]
        terminals_by_id = Terminal._base_manager.in_bulk(terminal_ids) if terminal_ids else {}
        missing_ids = [tid for tid in terminal_ids if tid not in terminals_by_id]
        if missing_ids:
            raise ValidationError(f"Terminal with ID {missing_ids[0]} does not exist")

        # 2) Bulk create new terminals (terminal_id is empty)
        new_terminal_pairs = []  # [(terminal_data, terminal_instance)]
        for terminal_data in terminals_data:
            if terminal_data.get('terminal_id'):
                continue
            terminal = Terminal(
                code=terminal_data.get('code'),
                name=terminal_data.get('name'),
                latitude=terminal_data.get('latitude'),
                longitude=terminal_data.get('longitude'),
            )
            new_terminal_pairs.append((terminal_data, terminal))

        if new_terminal_pairs:
            new_terminals = [t for _, t in new_terminal_pairs]
            Terminal.objects.bulk_create(new_terminals, batch_size=500)

            # Assign TEMP type for newly created terminals (bulk into M2M through table)
            temp_type = TerminalType.objects.get(code='TEMP')
            through = Terminal.terminal_types.through
            through.objects.bulk_create(
                [
                    through(terminal_id=t.id, terminaltype_id=temp_type.id)
                    for t in new_terminals
                    if t.id
                ],
                batch_size=1000,
                ignore_conflicts=True,
            )

        # 3) Bulk create / bulk update route terminals (delta)
        route_terminals_to_create = []
        route_terminals_to_update = []
        terminals_to_update = []
        new_terminal_iter = iter([t for _, t in new_terminal_pairs]) if new_terminal_pairs else iter([])
        for terminal_data in terminals_data:
            if terminal_data.get('terminal_id'):
                terminal = terminals_by_id[terminal_data.get('terminal_id')]
                # Update lat/long if provided (bulk_update later)
                updated = False
                if 'latitude' in terminal_data and terminal_data.get('latitude') is not None:
                    terminal.latitude = terminal_data.get('latitude')
                    updated = True
                if 'longitude' in terminal_data and terminal_data.get('longitude') is not None:
                    terminal.longitude = terminal_data.get('longitude')
                    updated = True
                if updated:
                    terminals_to_update.append(terminal)
            else:
                # Consume newly created terminals in the same order as input
                terminal = next(new_terminal_iter)

            order = terminal_data.get('order')
            existing_rt = existing_by_order.get(order)
            new_stop = terminal_data.get('stop', False)
            new_for_robot = terminal_data.get('for_robot', False)
            new_command_line = _maybe_json(terminal_data.get('command_line'))
            new_frame = _maybe_json(terminal_data.get('frame'))
            if existing_rt:
                # Only update if changed
                changed = False
                if existing_rt.terminal_id != terminal.id:
                    existing_rt.terminal = terminal
                    changed = True
                if existing_rt.stop != new_stop:
                    existing_rt.stop = new_stop
                    changed = True
                if existing_rt.for_robot != new_for_robot:
                    existing_rt.for_robot = new_for_robot
                    changed = True
                if existing_rt.command_line != new_command_line:
                    existing_rt.command_line = new_command_line
                    changed = True
                if existing_rt.frame != new_frame:
                    existing_rt.frame = new_frame
                    changed = True
                if changed:
                    route_terminals_to_update.append(existing_rt)
            else:
                route_terminals_to_create.append(
                    RouteTerminal(
                        route=route,
                        terminal=terminal,
                        stop=new_stop,
                        order=order,
                        for_robot=new_for_robot,
                        command_line=new_command_line,
                        frame=new_frame,
                    )
                )

        if route_terminals_to_create:
            RouteTerminal.objects.bulk_create(route_terminals_to_create, batch_size=500)
        if route_terminals_to_update:
            RouteTerminal.objects.bulk_update(
                route_terminals_to_update,
                ['terminal', 'stop', 'for_robot', 'command_line', 'frame'],
                batch_size=500,
            )

        if terminals_to_update:
            # De-duplicate terminals in case they appear multiple times
            unique_terminals_to_update = list({t.id: t for t in terminals_to_update if t.id}.values())
            Terminal.objects.bulk_update(unique_terminals_to_update, ['latitude', 'longitude'], batch_size=500)

        # 4) Bulk measurements
        # Fetch route_terminal ids for all incoming orders (1 query, ensures PKs exist)
        rt_rows = RouteTerminal.objects.filter(route=route, order__in=incoming_orders).values_list('order', 'id', 'terminal_id')
        rt_by_order = {order: {'id': rt_id, 'terminal_id': terminal_id} for order, rt_id, terminal_id in rt_rows}

        # 🚀 BULK measurements (replace per-item set_measurement N+1)
        ct_terminal = ContentType.objects.get_for_model(Terminal)

        # De-duplicate by entity id (last wins, matching old loop semantics)
        terminal_time_stops = {}
        rt_cruise_speed = {}
        rt_operating_altitude = {}

        for terminal_data in terminals_data:
            order = terminal_data.get('order')
            rt_info = rt_by_order.get(order)
            if not rt_info:
                continue

            terminal_id = rt_info.get('terminal_id')
            route_terminal_id = rt_info.get('id')

            # Use key-existence checks to handle 0 values correctly
            if terminal_id and ('time_stops' in terminal_data) and terminal_data.get('time_stops') is not None:
                terminal_time_stops[terminal_id] = terminal_data.get('time_stops')
            if route_terminal_id and ('cruise_speed' in terminal_data) and terminal_data.get('cruise_speed') is not None:
                rt_cruise_speed[route_terminal_id] = terminal_data.get('cruise_speed')
            if route_terminal_id and ('operating_altitude' in terminal_data) and terminal_data.get('operating_altitude') is not None:
                rt_operating_altitude[route_terminal_id] = terminal_data.get('operating_altitude')

        to_create = []
        to_update = []

        if terminal_time_stops:
            existing = list(
                Measurement.objects.filter(
                    content_type=ct_terminal,
                    object_id__in=list(terminal_time_stops.keys()),
                    measurement_type='time_stops',
                ).only('id', 'object_id', 'measurement_type', 'data')
            )
            existing_map = {m.object_id: m for m in existing}
            for terminal_id, raw_val in terminal_time_stops.items():
                data = _parse_simple_value_to_data(raw_val, default_unit='mins', context='time')
                if data:
                    m = existing_map.get(terminal_id)
                    if m:
                        if m.data != data:
                            m.data = data
                            to_update.append(m)
                    else:
                        to_create.append(
                            Measurement(
                                content_type=ct_terminal,
                                object_id=terminal_id,
                                measurement_type='time_stops',
                                data=data,
                            )
                        )

        if rt_cruise_speed or rt_operating_altitude:
            rt_ids = list(set(list(rt_cruise_speed.keys()) + list(rt_operating_altitude.keys())))
            existing = list(
                Measurement.objects.filter(
                    content_type=ct_route_terminal,
                    object_id__in=rt_ids,
                    measurement_type__in=['cruise_speed', 'operating_altitude'],
                ).only('id', 'object_id', 'measurement_type', 'data')
            )
            existing_map = {(m.object_id, m.measurement_type): m for m in existing}

            for rt_id, raw_val in rt_cruise_speed.items():
                data = _parse_simple_value_to_data(raw_val, default_unit='m/s', context='speed')
                if data:
                    m = existing_map.get((rt_id, 'cruise_speed'))
                    if m:
                        if m.data != data:
                            m.data = data
                            to_update.append(m)
                    else:
                        to_create.append(
                            Measurement(
                                content_type=ct_route_terminal,
                                object_id=rt_id,
                                measurement_type='cruise_speed',
                                data=data,
                            )
                        )
            for rt_id, raw_val in rt_operating_altitude.items():
                data = _parse_simple_value_to_data(raw_val, default_unit='m', context='length')
                if data:
                    m = existing_map.get((rt_id, 'operating_altitude'))
                    if m:
                        if m.data != data:
                            m.data = data
                            to_update.append(m)
                    else:
                        to_create.append(
                            Measurement(
                                content_type=ct_route_terminal,
                                object_id=rt_id,
                                measurement_type='operating_altitude',
                                data=data,
                            )
                        )

        if to_update:
            Measurement.objects.bulk_update(to_update, ['data'], batch_size=1000)
        if to_create:
            Measurement.objects.bulk_create(to_create, batch_size=1000)

    def _apply_route_terminals_patch(self, route, patch_data: dict):
        """
        Apply terminals patch (create/update/delete) without sending the full list.
        This is designed for very large routes where only a few terminals change.
        """
        def _maybe_json(value):
            if value and isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return value

        def _parse_simple_value_to_data(value, default_unit: str, context: str = None):
            from decimal import Decimal
            from devices.utils import standardize_unit
            if value is None:
                return None
            if isinstance(value, dict) and value.get('type'):
                return value
            if isinstance(value, (int, float, Decimal)):
                unit = standardize_unit(default_unit, context=context) if default_unit else default_unit
                return {'type': 'simple', 'value': float(value), 'unit': unit}
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return None
                import re
                m = re.search(r'(\d+(?:,\d+)*(?:\.\d+)?)\s*([a-zA-Z°%/\.]+)?', text)
                if not m:
                    return None
                num = m.group(1).replace(',', '')
                unit = (m.group(2) or default_unit or '').strip()
                unit = standardize_unit(unit, context=context) if unit else unit
                try:
                    return {'type': 'simple', 'value': float(num), 'unit': unit}
                except Exception:
                    return None
            return _parse_simple_value_to_data(str(value), default_unit, context=context)

        patch_data = patch_data or {}
        create_items = patch_data.get('create') or []
        update_items = patch_data.get('update') or []
        delete_ids = patch_data.get('delete') or []

        ct_route_terminal = ContentType.objects.get_for_model(RouteTerminal)
        ct_terminal = ContentType.objects.get_for_model(Terminal)

        # 1) DELETE
        if delete_ids:
            delete_qs = RouteTerminal.objects.filter(route=route, id__in=list(delete_ids))
            rt_ids_to_delete = list(delete_qs.values_list('id', flat=True))
            if rt_ids_to_delete:
                Measurement.objects.filter(
                    content_type=ct_route_terminal,
                    object_id__in=rt_ids_to_delete,
                ).delete()
                delete_qs.delete()

        # 2) Prepare update map (and validate ids)
        update_by_id = {}
        for item in update_items:
            rt_id = item.get('route_terminal_id')
            if not rt_id:
                raise ValidationError("route_terminal_id is required for terminals_patch.update items")
            update_by_id[int(rt_id)] = item

        # 3) Validate final orders uniqueness without scanning the whole route
        needs_order_validation = bool(create_items) or any(
            ('order' in item) and item.get('order') is not None for item in update_by_id.values()
        )
        if needs_order_validation:
            update_ids = list(update_by_id.keys())

            # orders for updated ids (old order if not changed, new order if changed)
            existing_orders_for_updates = dict(
                RouteTerminal.objects.filter(route=route, id__in=update_ids).values_list('id', 'order')
            ) if update_ids else {}
            missing_rt_ids = [rt_id for rt_id in update_ids if rt_id not in existing_orders_for_updates]
            if missing_rt_ids:
                raise ValidationError(f"RouteTerminal with ID {missing_rt_ids[0]} does not exist in this route")

            final_update_orders = []
            for rt_id, item in update_by_id.items():
                if ('order' in item) and item.get('order') is not None:
                    final_update_orders.append(int(item.get('order')))
                else:
                    final_update_orders.append(int(existing_orders_for_updates[rt_id]))

            new_orders = []
            for item in create_items:
                if item.get('order') is None:
                    raise ValidationError("order is required for terminals_patch.create items")
                new_orders.append(int(item.get('order')))

            combined = final_update_orders + new_orders
            if len(set(combined)) != len(combined):
                raise ValidationError("Duplicate 'order' values after applying terminals_patch")

            # Check collisions with unaffected route terminals (exclude updated ids)
            orders_to_check = list(set(combined))
            conflict_qs = RouteTerminal.objects.filter(route=route, order__in=orders_to_check).exclude(id__in=update_ids)
            if conflict_qs.exists():
                raise ValidationError("Duplicate 'order' values after applying terminals_patch")

        # 4) UPDATE existing RouteTerminal rows (only changed fields)
        route_terminals_to_update = []
        terminals_to_update = []

        # Load referenced terminals for reassignment (1 query)
        update_terminal_ids = [
            item.get('terminal_id') for item in update_by_id.values()
            if ('terminal_id' in item) and item.get('terminal_id') is not None
        ]
        terminals_by_id = Terminal._base_manager.in_bulk(update_terminal_ids) if update_terminal_ids else {}
        missing_terminal_ids = [tid for tid in update_terminal_ids if tid not in terminals_by_id]
        if missing_terminal_ids:
            raise ValidationError(f"Terminal with ID {missing_terminal_ids[0]} does not exist")

        if update_by_id:
            existing_rts = list(
                RouteTerminal.objects.filter(route=route, id__in=list(update_by_id.keys()))
                .select_related('terminal')
                .only('id', 'order', 'terminal_id', 'stop', 'for_robot', 'command_line', 'frame')
            )
            existing_map = {rt.id: rt for rt in existing_rts}
            missing_rt_ids = [rt_id for rt_id in update_by_id.keys() if rt_id not in existing_map]
            if missing_rt_ids:
                raise ValidationError(f"RouteTerminal with ID {missing_rt_ids[0]} does not exist in this route")

            for rt_id, item in update_by_id.items():
                rt = existing_map[rt_id]
                changed = False

                if ('terminal_id' in item) and item.get('terminal_id') is not None:
                    new_terminal = terminals_by_id[int(item.get('terminal_id'))]
                    if rt.terminal_id != new_terminal.id:
                        rt.terminal = new_terminal
                        changed = True

                if ('order' in item) and item.get('order') is not None and rt.order != int(item.get('order')):
                    rt.order = int(item.get('order'))
                    changed = True

                if ('stop' in item) and item.get('stop') is not None and rt.stop != bool(item.get('stop')):
                    rt.stop = bool(item.get('stop'))
                    changed = True

                if ('for_robot' in item) and item.get('for_robot') is not None and rt.for_robot != bool(item.get('for_robot')):
                    rt.for_robot = bool(item.get('for_robot'))
                    changed = True

                if 'command_line' in item:
                    new_cmd = _maybe_json(item.get('command_line'))
                    if rt.command_line != new_cmd:
                        rt.command_line = new_cmd
                        changed = True

                if 'frame' in item:
                    new_frame = _maybe_json(item.get('frame'))
                    if rt.frame != new_frame:
                        rt.frame = new_frame
                        changed = True

                # Update terminal lat/long if explicitly provided
                t = rt.terminal
                t_changed = False
                if ('latitude' in item) and item.get('latitude') is not None and str(t.latitude) != str(item.get('latitude')):
                    t.latitude = item.get('latitude')
                    t_changed = True
                if ('longitude' in item) and item.get('longitude') is not None and str(t.longitude) != str(item.get('longitude')):
                    t.longitude = item.get('longitude')
                    t_changed = True
                if t_changed:
                    terminals_to_update.append(t)

                if changed:
                    route_terminals_to_update.append(rt)

        if route_terminals_to_update:
            RouteTerminal.objects.bulk_update(
                route_terminals_to_update,
                ['terminal', 'stop', 'order', 'for_robot', 'command_line', 'frame'],
                batch_size=500,
            )

        if terminals_to_update:
            unique_terminals_to_update = list({t.id: t for t in terminals_to_update if t.id}.values())
            Terminal.objects.bulk_update(unique_terminals_to_update, ['latitude', 'longitude'], batch_size=500)

        # 5) CREATE new terminals (optional) and new RouteTerminal rows
        created_route_terminal_orders = []
        if create_items:
            # Existing terminals for create
            create_terminal_ids = [i.get('terminal_id') for i in create_items if i.get('terminal_id')]
            create_terminals_by_id = Terminal._base_manager.in_bulk(create_terminal_ids) if create_terminal_ids else {}
            missing_create_ids = [tid for tid in create_terminal_ids if tid not in create_terminals_by_id]
            if missing_create_ids:
                raise ValidationError(f"Terminal with ID {missing_create_ids[0]} does not exist")

            new_terminal_pairs = []  # [(item, terminal_obj)]
            for item in create_items:
                if item.get('terminal_id'):
                    continue
                terminal = Terminal(
                    code=item.get('code'),
                    name=item.get('name'),
                    latitude=item.get('latitude'),
                    longitude=item.get('longitude'),
                )
                new_terminal_pairs.append((item, terminal))

            if new_terminal_pairs:
                new_terminals = [t for _, t in new_terminal_pairs]
                Terminal.objects.bulk_create(new_terminals, batch_size=500)

                temp_type = TerminalType.objects.get(code='TEMP')
                through = Terminal.terminal_types.through
                through.objects.bulk_create(
                    [
                        through(terminal_id=t.id, terminaltype_id=temp_type.id)
                        for t in new_terminals
                        if t.id
                    ],
                    batch_size=1000,
                    ignore_conflicts=True,
                )

            # build RouteTerminal rows
            new_terminal_iter = iter([t for _, t in new_terminal_pairs]) if new_terminal_pairs else iter([])
            rts_to_create = []
            for item in create_items:
                if item.get('terminal_id'):
                    terminal = create_terminals_by_id[int(item.get('terminal_id'))]
                else:
                    terminal = next(new_terminal_iter)

                order = int(item.get('order'))
                rts_to_create.append(
                    RouteTerminal(
                        route=route,
                        terminal=terminal,
                        stop=bool(item.get('stop', False)),
                        order=order,
                        for_robot=bool(item.get('for_robot', False)),
                        command_line=_maybe_json(item.get('command_line')),
                        frame=_maybe_json(item.get('frame')),
                    )
                )
                created_route_terminal_orders.append(order)

            if rts_to_create:
                RouteTerminal.objects.bulk_create(rts_to_create, batch_size=500)

        # 6) BULK measurements for touched entities only
        terminal_time_stops = {}
        rt_cruise_speed = {}
        rt_operating_altitude = {}

        # Updates (avoid per-item queries)
        rt_ids_needing_terminal = [
            int(item.get('route_terminal_id')) for item in update_by_id.values()
            if ('time_stops' in item) and item.get('time_stops') is not None and item.get('terminal_id') is None
        ]
        rt_terminal_map = dict(
            RouteTerminal.objects.filter(route=route, id__in=rt_ids_needing_terminal).values_list('id', 'terminal_id')
        ) if rt_ids_needing_terminal else {}

        for item in update_by_id.values():
            rt_id = int(item.get('route_terminal_id'))
            if ('cruise_speed' in item) and item.get('cruise_speed') is not None:
                rt_cruise_speed[rt_id] = item.get('cruise_speed')
            if ('operating_altitude' in item) and item.get('operating_altitude') is not None:
                rt_operating_altitude[rt_id] = item.get('operating_altitude')
            if ('time_stops' in item) and item.get('time_stops') is not None:
                terminal_id = item.get('terminal_id') or rt_terminal_map.get(rt_id)
                if terminal_id:
                    terminal_time_stops[int(terminal_id)] = item.get('time_stops')

        # Creates: map created orders -> rt_id, terminal_id (1 query)
        if created_route_terminal_orders:
            created_rows = list(
                RouteTerminal.objects.filter(route=route, order__in=created_route_terminal_orders)
                .values_list('order', 'id', 'terminal_id')
            )
            created_by_order = {o: {'id': i, 'terminal_id': t} for o, i, t in created_rows}
            for item in create_items:
                order = int(item.get('order')) if item.get('order') is not None else None
                info = created_by_order.get(order) if order is not None else None
                if not info:
                    continue
                rt_id = info['id']
                terminal_id = info['terminal_id']
                if ('cruise_speed' in item) and item.get('cruise_speed') is not None:
                    rt_cruise_speed[rt_id] = item.get('cruise_speed')
                if ('operating_altitude' in item) and item.get('operating_altitude') is not None:
                    rt_operating_altitude[rt_id] = item.get('operating_altitude')
                if terminal_id and ('time_stops' in item) and item.get('time_stops') is not None:
                    terminal_time_stops[int(terminal_id)] = item.get('time_stops')

        to_create = []
        to_update = []

        if terminal_time_stops:
            existing = list(
                Measurement.objects.filter(
                    content_type=ct_terminal,
                    object_id__in=list(terminal_time_stops.keys()),
                    measurement_type='time_stops',
                ).only('id', 'object_id', 'measurement_type', 'data')
            )
            existing_map = {m.object_id: m for m in existing}
            for terminal_id, raw_val in terminal_time_stops.items():
                data = _parse_simple_value_to_data(raw_val, default_unit='mins', context='time')
                if data:
                    m = existing_map.get(terminal_id)
                    if m:
                        if m.data != data:
                            m.data = data
                            to_update.append(m)
                    else:
                        to_create.append(
                            Measurement(
                                content_type=ct_terminal,
                                object_id=terminal_id,
                                measurement_type='time_stops',
                                data=data,
                            )
                        )

        if rt_cruise_speed or rt_operating_altitude:
            rt_ids = list(set(list(rt_cruise_speed.keys()) + list(rt_operating_altitude.keys())))
            existing = list(
                Measurement.objects.filter(
                    content_type=ct_route_terminal,
                    object_id__in=rt_ids,
                    measurement_type__in=['cruise_speed', 'operating_altitude'],
                ).only('id', 'object_id', 'measurement_type', 'data')
            )
            existing_map = {(m.object_id, m.measurement_type): m for m in existing}
            for rt_id, raw_val in rt_cruise_speed.items():
                data = _parse_simple_value_to_data(raw_val, default_unit='m/s', context='speed')
                if data:
                    m = existing_map.get((rt_id, 'cruise_speed'))
                    if m:
                        if m.data != data:
                            m.data = data
                            to_update.append(m)
                    else:
                        to_create.append(
                            Measurement(
                                content_type=ct_route_terminal,
                                object_id=rt_id,
                                measurement_type='cruise_speed',
                                data=data,
                            )
                        )
            for rt_id, raw_val in rt_operating_altitude.items():
                data = _parse_simple_value_to_data(raw_val, default_unit='m', context='length')
                if data:
                    m = existing_map.get((rt_id, 'operating_altitude'))
                    if m:
                        if m.data != data:
                            m.data = data
                            to_update.append(m)
                    else:
                        to_create.append(
                            Measurement(
                                content_type=ct_route_terminal,
                                object_id=rt_id,
                                measurement_type='operating_altitude',
                                data=data,
                            )
                        )

        if to_update:
            Measurement.objects.bulk_update(to_update, ['data'], batch_size=1000)
        if to_create:
            Measurement.objects.bulk_create(to_create, batch_size=1000)
    
    @transaction.atomic
    def update_route(self, route_id, data):
        """
        Update an existing route
        
        Args:
            route_id: Route ID
            data: RouteUpdateSchema data
            
        Returns:
            tuple: (success, result)
        """
        try:
            # Get route
            try:
                route = Routes.objects.get(id=route_id)
            except Routes.DoesNotExist:
                return False, "Route not found"
            
            # Update route fields (excluding measurements and terminals)
            route_data = {k: v for k, v in data.items() 
                         if v is not None and k not in ['terminals', 'total_distance', 'estimated_time']}
            
            for field, value in route_data.items():
                setattr(route, field, value)
            
            # Update measurements if provided
            if data.get('total_distance'):
                route.set_measurement('total_distance', data.get('total_distance'))
                
            if data.get('estimated_time'):
                route.set_measurement('estimated_time', data.get('estimated_time'))
            
            route.save()
            
            # Update terminals if provided
            if data.get('terminals_patch') is not None:
                self._apply_route_terminals_patch(route, data.get('terminals_patch') or {})
            elif data.get('terminals'):
                terminals_data = data.get('terminals')
                self._create_route_terminals(route, terminals_data)
            
            return True, route
        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
    
    def get_route(self, route_id):
        """
        Get route by ID with related terminals
        
        Args:
            route_id: Route ID
            
        Returns:
            Queryset: Route với thông tin chi tiết về các terminal
        """
        try:
            # Lấy các terminals ordered by để tìm điểm đầu và điểm cuối
            first_terminal = RouteTerminal.objects.filter(
                route_id=OuterRef('id')
            ).order_by('order').values('terminal__name')[:1]
            
            last_terminal = RouteTerminal.objects.filter(
                route_id=OuterRef('id')
            ).order_by('-order').values('terminal__name')[:1]
            
            # 🚀 OPTIMIZED: Prefetch measurements cho RouteTerminal (cruise_speed, operating_altitude)
            # Prefetch measurements cho Terminal (time_stops)
            route_terminals_queryset = RouteTerminal.objects.filter(
                route_id=route_id
            ).select_related(
                'terminal',
                # 🚀 Avoid N+1 when TerminalOutSchema(fields="__all__") touches FK fields
                'terminal__location_type',
                'terminal__terminal_purpose',
                'terminal__purpose_type',
                'terminal__deactivate_reason',
                'terminal__avatar',
            ).prefetch_related(
                'terminal__terminal_types',
                'terminal__functions',
                'terminal__operating_times__day_of_week',
                'terminal__exceptions',
                # GenericRelation - prevents N+1 if schema includes attachments
                'terminal__file_attachments',
                'measurements',  # Prefetch measurements cho RouteTerminal
                'terminal__measurements'  # Prefetch measurements cho Terminal
            ).annotate(
                terminal_name=F('terminal__name'),
                latitude=F('terminal__latitude'),
                longitude=F('terminal__longitude'),
                note=F('terminal__note')
            ).order_by('order', 'id')
            
            # Sử dụng Prefetch để prefetch các route_terminals đã được annotate
            route_terminals_prefetch = Prefetch(
                'route_terminals',
                queryset=route_terminals_queryset
            )
            
            # 🚀 OPTIMIZED: Prefetch measurements cho Route (total_distance, estimated_time)
            # Truy vấn route với annotations cho start_point và end_point
            # và prefetch các route_terminals đã được annotate cùng với measurements
            route_queryset = Routes.objects.filter(id=route_id).annotate(
                start_point=Subquery(first_terminal),
                end_point=Subquery(last_terminal),
            ).prefetch_related(
                route_terminals_prefetch,
                'measurements'  # Prefetch measurements cho Route
            ).select_related('terminal_from').first()
            # Return queryset
            return route_queryset
        except Exception:
            return Routes.objects.none()
    
    def get_routes(self, query_params=None):
        """
        Get all routes with optional filtering
        
        Args:
            query_params: Optional query parameters for filtering
            
        Returns:
            Queryset: Routes với thông tin đầy đủ
        """
        # Lấy các terminals ordered by để tìm điểm đầu và điểm cuối
        first_terminal = RouteTerminal.objects.filter(
            route_id=OuterRef('id')
        ).order_by('order').values('terminal__name')[:1]
        
        last_terminal = RouteTerminal.objects.filter(
            route_id=OuterRef('id')
        ).order_by('-order').values('terminal__name')[:1]
        
        # Tạo queryset cho RouteTerminal với thông tin tên terminal
        # Chỉ cần thông tin cơ bản cho list view
        route_terminals_queryset = RouteTerminal.objects.select_related(
            'terminal'
        ).annotate(
            terminal_name=F('terminal__name')
        ).order_by('order')
        
        # Sử dụng Prefetch để prefetch các route_terminals
        route_terminals_prefetch = Prefetch(
            'route_terminals',
            queryset=route_terminals_queryset
        )
        
        # Check if route is used in delivery operations
        from delivery.models import DeliveryOperation
        delivery_exists_expr = Exists(
            DeliveryOperation.objects.filter(route_id=OuterRef('id'))
        )
        
        # Check if route is used in surveillance missions
        # Route can be used if drone_segments contains route_id
        # For PostgreSQL: Use jsonb_array_elements to check each segment
        
        # Check if any mission has drone_segments containing this route_id
        # Using PostgreSQL-specific JSON functions with RawSQL
        # We use RawSQL directly in annotation to check if route_id exists in any mission's drone_segments
        routes_table = Routes._meta.db_table
        surveillance_exists_expr = RawSQL(
            f"""
            EXISTS (
                SELECT 1 
                FROM surveillance_surveymission
                WHERE drone_segments IS NOT NULL
                AND EXISTS (
                    SELECT 1 
                    FROM jsonb_array_elements(drone_segments) AS segment
                    WHERE (segment->>'route_id')::int = {routes_table}.id
                )
            )
            """,
            [],
            output_field=BooleanField()
        )
        
        # Build in_use annotation as a string combining both checks
        # First annotate the existence checks, then use them in Case/When
        routes_queryset = Routes.objects.annotate(
            start_point=Subquery(first_terminal),
            end_point=Subquery(last_terminal),
            delivery_exists=delivery_exists_expr,
            surveillance_exists=surveillance_exists_expr,
            in_use=Case(
                When(
                    delivery_exists=True,
                    surveillance_exists=True,
                    then=Value(True)
                ),
                When(
                    delivery_exists=True,
                    then=Value(True)
                ),
                When(
                    surveillance_exists=True,
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField()
            ),
            route_service__name=F('route_service__name')
        ).prefetch_related(
            route_terminals_prefetch
        ).select_related('terminal_from', 'route_service').order_by('-id')
        
        return routes_queryset
    
    @transaction.atomic
    def delete_route(self, route_ids):
        """
        Delete a route
        
        Args:
            route_ids: Route IDs
            
        Returns:
            tuple: (success, result)
        """
        try:
            route_id_list = [int(id.strip()) for id in route_ids.split(',')]
            routes = Routes.objects.filter(id__in=route_id_list)
            for route in routes:
                RouteTerminal.objects.filter(route=route).delete()
                route.delete()
            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DELETE_SUCCESS)
        except Exception as e:
            return False, str(e)

    @transaction.atomic
    def change_status(self, ids: str):
        """
        Change the status of a route
        """
        try:
            ids = ids.split(',')
            routes = Routes.objects.filter(id__in=ids)
            for route in routes:
                route.is_active = not route.is_active
                route.save()
            return True, "Routes status changed successfully"
        except Exception as e:
            return False, str(e)

    def activate(self, ids: str):
        """
        Activate routes
        """
        try:
            ids = ids.split(',')
            routes = Routes.objects.filter(id__in=ids)
            for route in routes:
                route.is_active = True
                route.save()
            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_ACTIVATE_SUCCESS)
        except Exception as e:
            return False, str(e)

    def deactivate(self, ids: str):
        """
        Deactivate routes
        """
        try:
            ids = ids.split(',')    
            routes = Routes.objects.filter(id__in=ids)
            for route in routes:
                route.is_active = False
                route.save()
            return True, MESSAGE_ENUM.get(MESSAGE_ENUM.ACTION_DEACTIVATE_SUCCESS)
        except Exception as e:
            return False, str(e)