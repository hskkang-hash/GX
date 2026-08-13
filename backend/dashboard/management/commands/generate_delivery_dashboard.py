import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import Dashboard, DashboardPanel

class Command(BaseCommand):
    help = "Generate a delivery dashboard with panels and data"

    def handle(self, *args, **options):
        self.stdout.write("Starting to generate delivery dashboard...")

        dashboard, created = Dashboard.objects.update_or_create(
            code="delivery_dashboard",
            defaults={
                "name": "Delivery Dashboard",
                "layout_config": {},
                "data_updated_at": timezone.now()
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Dashboard "{dashboard.name}" created.'))

            # Clear existing panels
            DashboardPanel.objects.filter(dashboard=dashboard).delete()
            self.stdout.write(self.style.SUCCESS(f'Cleared existing panels for "{dashboard.name}".'))

            # Panel 1: Donut Chart - Order Status
            panel1_data = {
                "data": [
                    {
                        "label": "Received",
                        "value": 100,
                        "color": {
                            "light": "#43bcff",
                            "dark": "#43bcff"
                        }
                    },
                    {
                        "label": "Pending Shipment",
                        "value": 50,
                        "color": {
                            "light": "#ffda45",
                            "dark": "#ffda45"
                        }
                    },
                    {
                        "label": "In Transit",
                        "value": 50,
                        "color": {
                            "light": "#fba640",
                            "dark": "#fba640"
                        }
                    },
                    {
                        "label": "Shipped",
                        "value": 25,
                        "color": {
                            "light": "#54d586",
                            "dark": "#54d586"
                        }
                    },
                    {
                        "label": "Cancelled",
                        "value": 24,
                        "color": {
                            "light": "#fe5246",
                            "dark": "#fe5246"
                        }
                    }
                ]
            }
            DashboardPanel.objects.create(
                dashboard=dashboard,
                panel_title="Delivery Progress",
                panel_type="donut_chart",
                panel_config={"type": "donut", "field": "series"},
                panel_data=panel1_data
            )

            # Panel 2: Metric - Received
            panel2_data = {
                "data": [
                    {
                        "label": "This Month",
                        "value": 154,
                        "color": {
                            "light": "#41bbff",
                            "dark": "#41bbff"
                        }
                    },
                    {
                        "label": "Last Month",
                        "value": 159,
                        "color": {
                            "light": "#675ed1",
                            "dark": "#675ed1"
                        }
                    }
                ]
            }
            DashboardPanel.objects.create(
                dashboard=dashboard,
                panel_title="Received",
                panel_type="metric",
                panel_config={"icon": "bell"},
                panel_data=panel2_data
            )

            # Panel 3: Metric - Completion vs Cancellation
            panel3_data = {
                "data": [
                    {
                        "label": "Shipped",
                        "value": 100,
                        "color": {
                            "light": "#41bbff",
                            "dark": "#41bbff"
                        }
                    },
                    {
                        "label": "Cancelled",
                        "value": 41,
                        "color": {
                            "light": "#fe5246",
                            "dark": "#fe5246"
                        }
                    }
                ]
            }
            DashboardPanel.objects.create(
                dashboard=dashboard,
                panel_title="Completion vs Cancellation",
                panel_type="metric",
                panel_config={"icon": "clipboard-check"},
                panel_data=panel3_data
            )

            # Panel 4: Metric - Pending Shipment vs In Transit
            panel4_data = {
                "data": [
                    {
                        "label": "Pending Shipment",
                        "value": 80,
                        "color": {
                            "light": "#ffda45",
                            "dark": "#ffda45"
                        }
                    },
                    {
                        "label": "In Transit",
                        "value": 134,
                        "color": {
                            "light": "#fba640",
                            "dark": "#fba640"
                        }
                    }
                ]
            }
            DashboardPanel.objects.create(
                dashboard=dashboard,
                panel_title="Pending Shipment vs In Transit",
                panel_type="metric",
                panel_config={"icon": "calendar"},
                panel_data=panel4_data
            )
            
            # Panel 5: Bar Chart - Monthly Delivery Stats
            panel5_data = {
                "data": [
                    {
                        "label": "May",
                        "value": 56,
                        "color": {
                            "light": "#42bbfe",
                            "dark": "#42bbfe"
                        }
                    },
                    {
                        "label": "June",
                        "value": 64,
                        "color": {
                            "light": "#42bbfe",
                            "dark": "#42bbfe"
                        }
                    },
                    {
                        "label": "July",
                        "value": 76,
                        "color": {
                            "light": "#42bbfe",
                            "dark": "#42bbfe"
                        }
                    }
                ]
            }
            DashboardPanel.objects.create(
                dashboard=dashboard,
                panel_title="Monthly Delivery Stats",
                panel_type="bar_chart",
                panel_config={"type": "bar", "x_axis": "month", "y_axis": "deliveries"},
                panel_data=panel5_data
            )

            # Panel 6: Key-Value - Order Stats by Item Type
            panel6_data = {
                "data": [
                    {
                        "label": "Food",
                        "value": 531,
                        "color": {
                            "light": "#42bbfe",
                            "dark": "#42bbfe"
                        }
                    },
                    {
                        "label": "Clothing",
                        "value": 305,
                        "color": {
                            "light": "#42bbfe",
                            "dark": "#42bbfe"
                        }
                    },
                    {
                        "label": "Electronics",
                        "value": 363,
                        "color": {
                            "light": "#42bbfe",
                            "dark": "#42bbfe"
                        }
                    },
                    {
                        "label": "Documents",
                        "value": 172,
                        "color": {
                            "light": "#42bbfe",
                            "dark": "#42bbfe"
                        }
                    },
                    {
                        "label": "Other",
                        "value": 568,
                        "color": {
                            "light": "#42bbfe",
                            "dark": "#42bbfe"
                        }
                    }
                ]
            }
            DashboardPanel.objects.create(
                dashboard=dashboard,
                panel_title="Order Stats by Item Type",
                panel_type="item_metric",
                panel_config={"icon": "package", "columns": ["item_type", "count"]},
                panel_data=panel6_data
            )

            # Panel 7: Key-Value - Regional Order Stats
            panel7_data = {
                "data": [
                    {
                        "label": "Region 1",
                        "value": 100,
                        "color": {
                            "light": "#6e45e3",
                            "dark": "#6e45e3"
                        }
                    },
                    {
                        "label": "Region 2",
                        "value": 154,
                        "color": {
                            "light": "#6e45e3",
                            "dark": "#6e45e3"
                        }
                    },
                    {
                        "label": "Incheon",
                        "value": 159,
                        "color": {
                            "light": "#6e45e3",
                            "dark": "#6e45e3"
                        }
                    }
                ]
            }
            DashboardPanel.objects.create(
                dashboard=dashboard,
                panel_title="Regional Order Stats",
                panel_type="mono_color_metric",
                panel_config={"icon": "building", "columns": ["region", "count"]},
                panel_data=panel7_data
            )

            # Panel 8: Key-Value - Order Stats by Weight
            panel8_data = {
                "data": [
                    {
                        "label": "0-2kg",
                        "value": 100,
                        "color": {
                            "light": "#6e45e3",
                            "dark": "#6e45e3"
                        }
                    },
                    {
                        "label": "2-5kg",
                        "value": 154,
                        "color": {
                            "light": "#6e45e3",
                            "dark": "#6e45e3"
                        }
                    },
                    {
                        "label": "Over 5kg",
                        "value": 159,
                        "color": {
                            "light": "#6e45e3",
                            "dark": "#6e45e3"
                        }
                    }
                ]
            }
            DashboardPanel.objects.create(
                dashboard=dashboard,
                panel_title="Order Stats by Weight",
                panel_type="mono_color_metric",
                panel_config={"icon": "weight", "columns": ["weight_range", "count"]},
                panel_data=panel8_data
            )

            self.stdout.write(self.style.SUCCESS("Successfully generated delivery dashboard.")) 
        else:
            self.stdout.write(self.style.SUCCESS(f'Dashboard "{dashboard.name}" updated.'))
