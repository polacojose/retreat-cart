from enum import Enum
from typing import Self

import nltk
from nltk.stem.wordnet import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

nltk.download("wordnet")
lemmatizer = WordNetLemmatizer()


def clean_text(text):
    # This splits the text into words, makes them lowercase, and removes plurals
    # e.g., "Fruits" -> "fruit", "herbs" -> "herb"
    words = text.lower().replace("&", "").replace(",", "").split()
    return " ".join([lemmatizer.lemmatize(word) for word in words])


# Initialize category vector for rapid repeated use.
vectorizer = TfidfVectorizer(stop_words="english")


class Category(str, Enum):
    FruitVegetables = "Fruits Vegetables"
    MeatPoultrySeafood = "Meat Poultry Seafood"
    FridgeDeliEggs = "Fridge Deli Eggs"
    Bakery = "Bakery Breads"
    Frozen = "Frozen"
    Pantry = "Pantry"
    HotColdDrinks = "Drinks"
    BeerWineCider = "Beer Wine Cider"
    HealthBody = "Health Body"
    BabyToddler = "Baby Toddler"
    Pets = "Pets"
    HouseholdCleaning = "Household Cleaning"
    SnacksTreatsEasyMeals = "Snacks Treats Easy Meals"
    Other = "Other"

    @classmethod
    def best_guess(cls, query: str) -> Self:

        query = clean_text(query)
        query_vector = vectorizer.transform([query])

        max_score = 0
        max_category = Category.Other
        for i, score in enumerate(cosine_similarity(query_vector, category_vectors)[0]):
            if score > max_score:
                max_score = score
                max_category = categories[i]

        return max_category  # ty:ignore[invalid-return-type]


categories = [c for c in Category]
category_vectors = vectorizer.fit_transform([clean_text(c.value) for c in categories])
