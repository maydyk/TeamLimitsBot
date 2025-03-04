"""
modeule 'international'
Load and setup localization files for aiogram.
NOTE: Don't change module location!

To process messages run in the shell:
1. extract messages from code to generate template ./locales/messages.pot
pybabel extract --input-dirs=. -o locales/messages.pot

2. update po files:
pybabel update -d locales -D messages -i locales/messages.pot

3: Manually edit files ./locales/**/LC_MESSAGES/messages.po

4: compile mo files:
pybabel compile -f -d locales -D messages

@Author: Denis Maydykovsky
"""
# See instructons how to prepare localization files
# https://docs.aiogram.dev/en/stable/utils/i18n.html#step-1-extract-messages

from aiogram import Bot, Router
from aiogram_dialog.api.protocols import DialogManager
from aiogram_dialog.widgets.text import Const, Format, Jinja
from aiogram_dialog.widgets.text.format import _FormatDataStub
from aiogram_dialog.widgets.text.jinja import JINJA_ENV_FIELD , default_env
from aiogram_dialog.widgets.common import WhenCondition
from aiogram.utils.i18n import I18n
from aiogram.utils.i18n.middleware import FSMI18nMiddleware
from jinja2 import BaseLoader, Environment
from pathlib import Path

# Setup localization directory
BASE_DIR = Path(__file__).parent
LOCALES_DIR = BASE_DIR / "locales"

# Setup i18n middleware
__i18n = I18n(path=LOCALES_DIR)
__localization = FSMI18nMiddleware(__i18n)

def localize_router(router: Router):
    __localization.setup(router)

# Alias for gettext method
_ = __i18n.gettext

# Alias for dialogs. This is the one of default bybabel prefixes. 
def N_(text: str) -> str: return text

class NConst(Const):
    '''
    Use this class instead Const to localize strings.
    Use prefix N_(...)
    '''
    async def _render_text(self, data: dict, manager: DialogManager) -> str:
        return _(self.text)
    
class NJinja(Jinja):
    async def _render_text(self, data: dict, manager: DialogManager) -> str:
        if JINJA_ENV_FIELD in manager.middleware_data:
            env = manager.middleware_data[JINJA_ENV_FIELD]
        else:
            bot: Bot = manager.middleware_data.get("bot")
            env: Environment = getattr(bot, JINJA_ENV_FIELD, default_env)
        template = env.get_template(_(self.template_text))

        if env.is_async:
            return await template.render_async(data)
        else:
            return template.render(data)
        
class NFormat(Format):
    async def _render_text(
            self, data: dict, manager: DialogManager,
    ) -> str:
        if manager.is_preview():
            return _(self.text).format_map(_FormatDataStub(data=data))
        return _(self.text).format_map(data)


