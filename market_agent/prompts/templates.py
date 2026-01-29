from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..config.settings import Config

class TemplateManager:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(Config.PROMPTS_DIR)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def render(self, template_name: str, **kwargs) -> str:
        template = self.env.get_template(template_name)
        return template.render(**kwargs)