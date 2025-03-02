'''
modeule 'international'
Load and setup localization files for aiogram.
NOTE: Don't change module location!

@Author: Denis Maydykovsky
'''
from aiogram.utils.i18n import I18n, gettext as _
from aiogram.utils.i18n.middleware import SimpleI18nMiddleware
from pathlib import Path

# Setup localization directory and domain
I18N_DOMAIN = 'messages'
BASE_DIR = Path(__file__).parent
LOCALES_DIR = BASE_DIR / "locales"

# Setup i18n middleware
__i18n = I18n(path=LOCALES_DIR, default_locale="en", domain=I18N_DOMAIN)    
localization = SimpleI18nMiddleware(__i18n)
# Alias for gettext method
_ = __i18n.gettext
