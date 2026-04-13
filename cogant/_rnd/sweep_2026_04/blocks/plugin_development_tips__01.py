import logging
from cogant.translate.engine import TranslationRule

logger = logging.getLogger(__name__)

class MyTranslationRule(TranslationRule):
    def apply(self, match, graph, query):
        logger.debug(f"Applying rule to {match['name']}")
        # ...
        logger.info(f"Assigned concept {mapping.target_concept}")
        return mapping
