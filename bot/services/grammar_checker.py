import language_tool_python
import re
from typing import List, Dict

class GrammarChecker:
    def __init__(self):
        # Inicializar LanguageTool para inglês
        self.tool = language_tool_python.LanguageTool('en-US')
        
        # Regras customizadas para erros comuns de brasileiros
        self.brazilian_common_errors = [
            {
                'pattern': r'\b(make|do)\s+(the\s+)?homework\b',
                'correct': 'do homework',
                'rule': 'Use "do" with homework, not "make"'
            },
            {
                'pattern': r'\bhave\s+\d+\s+years\b',
                'correct': 'be X years old',
                'rule': 'Use "I am X years old" not "I have X years"'
            },
            {
                'pattern': r'\b(is|are)\s+a\s+lot\s+of\s+people\b',
                'correct': 'there are a lot of people',
                'rule': 'Use "there are" for existence, not just "are"'
            }
        ]
    
    def check(self, text: str) -> List[Dict]:
        """Verifica erros gramaticais no texto"""
        errors = []
        
        # Verificar com LanguageTool
        matches = self.tool.check(text)
        
        for match in matches[:5]:  # Limitar a 5 erros principais
            # Ignorar alguns tipos de erro menos importantes
            if match.ruleId in ['WHITESPACE_RULE', 'COMMA_PARENTHESIS_WHITESPACE']:
                continue
                
            errors.append({
                'rule': match.message,
                'category': match.category,
                'offset': match.offset,
                'length': match.errorLength,
                'suggestions': match.replacements[:3],
                'context': match.context,
                'original': text[match.offset:match.offset + match.errorLength]
            })
        
        # Verificar erros comuns de brasileiros
        for error_rule in self.brazilian_common_errors:
            if re.search(error_rule['pattern'], text, re.IGNORECASE):
                errors.append({
                    'rule': error_rule['rule'],
                    'category': 'Brazilian Common Error',
                    'correct': error_rule['correct'],
                    'suggestions': [error_rule['correct']]
                })
        
        return errors
    
    def format_corrections_portuguese(self, errors: List[Dict]) -> str:
        """Formata correções em português"""
        if not errors:
            return ""
        
        corrections = ["📝 **Correções e Dicas:**\n"]
        
        for i, error in enumerate(errors, 1):
            original = error.get('original', '')
            suggestions = error.get('suggestions', [])
            
            correction_text = f"{i}. "
            
            # Traduzir categoria de erro
            category_translations = {
                'Grammar': 'Gramática',
                'Spelling': 'Ortografia',
                'Punctuation': 'Pontuação',
                'Style': 'Estilo',
                'Brazilian Common Error': 'Erro Comum de Brasileiros'
            }
            
            category = category_translations.get(
                error.get('category', 'Grammar'),
                'Gramática'
            )
            
            correction_text += f"**{category}**: "
            
            if original:
                correction_text += f'Você escreveu "{original}"'
                if suggestions:
                    correction_text += f', o correto seria "{suggestions[0]}"'
            
            correction_text += f"\n   💡 {error['rule']}\n"
            
            corrections.append(correction_text)
        
        return "\n".join(corrections)
