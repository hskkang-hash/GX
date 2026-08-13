from django.core.management.base import BaseCommand
from report_template.models import ReportTemplate


class Command(BaseCommand):
    help = 'Manage report templates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all templates',
        )
        parser.add_argument(
            '--set-default',
            type=int,
            help='Set template with given ID as default',
        )
        parser.add_argument(
            '--enable',
            type=int,
            help='Enable template with given ID',
        )
        parser.add_argument(
            '--disable',
            type=int,
            help='Disable template with given ID',
        )
        parser.add_argument(
            '--delete',
            type=int,
            help='Delete template with given ID',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remove default flag from all templates except the first one',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_templates()
        elif options['set_default']:
            self.set_default_template(options['set_default'])
        elif options['enable']:
            self.enable_template(options['enable'])
        elif options['disable']:
            self.disable_template(options['disable'])
        elif options['delete']:
            self.delete_template(options['delete'])
        elif options['cleanup']:
            self.cleanup_defaults()
        else:
            self.stdout.write(self.style.ERROR('Please specify an action. Use --help for options.'))
            self.list_templates()

    def list_templates(self):
        """List all templates with their details"""
        templates = ReportTemplate.objects.all().order_by('id')
        
        if not templates.exists():
            self.stdout.write(self.style.WARNING('No templates found in database.'))
            return
        
        self.stdout.write(f"\nFound {templates.count()} template(s):")
        self.stdout.write("-" * 80)
        
        for template in templates:
            status = "✅" if template.is_enabled else "❌"
            default = "⭐" if template.is_default else "  "
            self.stdout.write(
                f"{default} {status} ID: {template.id:2d} | "
                f"Name: {template.name:<30} | "
                f"Default: {str(template.is_default):<5} | "
                f"Enabled: {str(template.is_enabled):<5} | "
                f"Usage: {template.usage_count}"
            )
        
        self.stdout.write("-" * 80)

    def set_default_template(self, template_id):
        """Set a template as default"""
        try:
            template = ReportTemplate.objects.get(id=template_id)
            
            # Remove default flag from all other templates
            ReportTemplate.objects.exclude(id=template_id).update(is_default=False)
            
            # Set this template as default
            template.is_default = True
            template.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Template "{template.name}" (ID: {template_id}) is now the default template.')
            )
            
        except ReportTemplate.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Template with ID {template_id} does not exist.')
            )

    def enable_template(self, template_id):
        """Enable a template"""
        try:
            template = ReportTemplate.objects.get(id=template_id)
            template.is_enabled = True
            template.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Template "{template.name}" (ID: {template_id}) has been enabled.')
            )
            
        except ReportTemplate.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Template with ID {template_id} does not exist.')
            )

    def disable_template(self, template_id):
        """Disable a template"""
        try:
            template = ReportTemplate.objects.get(id=template_id)
            
            # Don't allow disabling the default template
            if template.is_default:
                self.stdout.write(
                    self.style.ERROR(f'Cannot disable default template "{template.name}" (ID: {template_id}). Set another template as default first.')
                )
                return
            
            template.is_enabled = False
            template.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Template "{template.name}" (ID: {template_id}) has been disabled.')
            )
            
        except ReportTemplate.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Template with ID {template_id} does not exist.')
            )

    def delete_template(self, template_id):
        """Delete a template"""
        try:
            template = ReportTemplate.objects.get(id=template_id)
            
            # Don't allow deleting the default template
            if template.is_default:
                self.stdout.write(
                    self.style.ERROR(f'Cannot delete default template "{template.name}" (ID: {template_id}). Set another template as default first.')
                )
                return
            
            name = template.name
            template.delete()
            
            self.stdout.write(
                self.style.SUCCESS(f'Template "{name}" (ID: {template_id}) has been deleted.')
            )
            
        except ReportTemplate.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Template with ID {template_id} does not exist.')
            )

    def cleanup_defaults(self):
        """Remove default flag from all templates except the first one"""
        templates = ReportTemplate.objects.filter(is_default=True).order_by('id')
        
        if templates.count() <= 1:
            self.stdout.write(
                self.style.WARNING('No cleanup needed. Only one or zero default templates found.')
            )
            return
        
        # Keep the first one as default, remove from others
        first_template = templates.first()
        others = templates.exclude(id=first_template.id)
        
        count = others.count()
        others.update(is_default=False)
        
        self.stdout.write(
            self.style.SUCCESS(f'Cleanup completed. Removed default flag from {count} template(s).')
        )
        self.stdout.write(
            f'Template "{first_template.name}" (ID: {first_template.id}) remains as the default.'
        )
