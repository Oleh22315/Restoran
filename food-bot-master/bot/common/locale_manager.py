import os, json
from pathlib import Path
from typing import List


class LocaleManager:
    USER_LOCALS = {}

    class Locale:
        def __init__(self, path) -> None:
            self.data = {}
            with open(path, encoding="utf-8") as file:
                self.data = json.load(file)

        def get(self, raw_key: str) -> str:
            keys = raw_key.split(".")

            result = self.data
            for key in keys:
                result = result[key]

            return result

    def __init__(self, locales_dir) -> None:
        self.loaded_locales = {}

        for path in Path(locales_dir).iterdir():
            self.loaded_locales[Path(path).stem] = self.Locale(path)

    def get_locale(self, locale) -> Locale:
        return self.loaded_locales[locale]
