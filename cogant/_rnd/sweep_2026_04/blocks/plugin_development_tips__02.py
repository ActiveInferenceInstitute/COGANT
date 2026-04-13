from cogant.plugins import LanguagePlugin

class MyParserPlugin(LanguagePlugin):
    def parse(self, source_code: str):
        try:
            ast = self._parse_entities(source_code)
            return {"ast": ast, "errors": [], "warnings": []}
        except Exception as e:
            return {"ast": [], "errors": [str(e)], "warnings": []}
