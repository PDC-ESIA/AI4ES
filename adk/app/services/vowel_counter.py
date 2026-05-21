from typing import Dict

class VowelCounterService:
    VOWELS = ['a', 'e', 'i', 'o', 'u']

    @staticmethod
    def count_vowels(text: str) -> Dict[str, int]:
        counts = {vowel: 0 for vowel in VowelCounterService.VOWELS}
        for char in text.lower():
            if char in counts:
                counts[char] += 1
        return counts

    @staticmethod
    def total_vowels(counts: Dict[str, int]) -> int:
        return sum(counts.values())
