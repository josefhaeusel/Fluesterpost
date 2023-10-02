## Converts an English text to International Phonetic Alphabet

import eng_to_ipa as ipa

eng_text = ("hello world")
ipa_text = ipa.convert(eng_text)

print("\n English text: \n", eng_text)
print("\n", "IPA text: \n", ipa_text)