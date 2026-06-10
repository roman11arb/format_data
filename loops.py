numbers = [10, 2, 54, 644, 23, 54, 65, 6, 54, 64, 45]
string = "Python"

vowels = ("a", "e", "i", "o", "u")
sentence = "Take a list of numbers and calculate their total sum without using"
count = 0

for letter in sentence:
    if letter in vowels:
        count += 1

print(count)
