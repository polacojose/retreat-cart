from enum import Enum
from typing import Optional, Self, Union

import nltk
from nltk.stem.wordnet import WordNetLemmatizer
from pydantic import BaseModel, field_validator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Used by the lemmatizer
nltk.download("wordnet")
lemmatizer = WordNetLemmatizer()


def clean_text(text):
    # This splits the text into words, makes them lowercase, and removes plurals
    # e.g., "Fruits" -> "fruit", "herbs" -> "herb"
    words = text.lower().replace("&", "").replace(",", "").split()
    return " ".join([lemmatizer.lemmatize(word) for word in words])


class Measurement(str, Enum):
    Gram = "g"
    Milliliters = "ml"
    Each = "each"


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


class CartParameters(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    increment: Optional[float] = None


class ProductBase(BaseModel):
    id: str
    name: str
    category: Optional[Category]

    @field_validator("category", mode="before")
    @classmethod
    def eval(cls, value: str) -> Category:
        if value in Category:
            return Category(value)
        else:
            return Category.Other


class ProductRequest(ProductBase):
    amount: Optional[float] = None
    measurement: Measurement


class ProductError(BaseModel):
    message: str
    exception_error_message: Optional[str] = None


type PossibleProductResponse = Union[ProductResponse, ProductError]


class Value(BaseModel):
    cost_per: float
    number: float
    measure: Measurement


class ProductResponse(ProductBase):
    cost_per_unit: float
    value: Optional[Value] = None
    cart_parameters: Optional[CartParameters] = None

    @field_validator("category", mode="before")
    @classmethod
    def eval(cls, value: str) -> Category:
        if value in Category:
            return Category(value)
        else:
            return Category.Other
