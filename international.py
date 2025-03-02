'''
modeule 'international'
Load and setup localization files for aiogram.
NOTE: Don't change module location!

To process messages run in the shell:
1. extract messages from code to generate template ./locales/messages.pot
pybabel extract -k _T --input-dirs=. -o locales/messages.pot

2. update po files:
pybabel update -d locales -D messages -i locales/messages.pot

3: Manually edit files ./locales/**/LC_MESSAGES/messages.po

4: compile mo files:
pybabel compile -f -d locales -D messages

@Author: Denis Maydykovsky
'''
# See instructons how to prepare localization files
# https://docs.aiogram.dev/en/stable/utils/i18n.html#step-1-extract-messages

from aiogram import Router
from aiogram_dialog.api.protocols import DialogManager
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.common import WhenCondition
from aiogram.utils.i18n import I18n
from aiogram.utils.i18n.middleware import FSMI18nMiddleware
from pathlib import Path

# Setup localization directory
BASE_DIR = Path(__file__).parent
LOCALES_DIR = BASE_DIR / "locales"

# Setup i18n middleware
__i18n = I18n(path=LOCALES_DIR)
__localization = FSMI18nMiddleware(__i18n)

def setup_router(router: Router):
    __localization.setup(router)

# Alias for gettext method
_ = __i18n.gettext

# Alias for dialogs
def _T(text: str) -> str:
    return text

class I18nFormat(Text):
    '''
    Use this class instead Const to localize strings.
    Use prefix _T(...)
    '''
    def __init__(self, text: str, when: WhenCondition = None):
        super().__init__(when)
        self.text = text

    async def _render_text(self, data: dict, manager: DialogManager) -> str:
        return _(self.text)


