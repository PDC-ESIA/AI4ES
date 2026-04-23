class VowelCounterService:
    @staticmethod
    def count_vowels(text: str) -> int:
        # Contabiliza vogais maiúsculas e minúsculas
        vowels = set('aeiouAEIOU')
        return sum(1 for c in text if c in vowels)
