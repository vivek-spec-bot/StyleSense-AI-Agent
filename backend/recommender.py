from __future__ import annotations

import csv
import os
from collections import Counter
from statistics import mean

import requests


class StyleSenseEngine:
    def __init__(self, store) -> None:
        self.store = store
        self.dataset = self._load_dataset()

    def _load_dataset(self) -> list[dict]:
        rows = []
        dataset_path = os.path.join(self.store.base_dir, "datasets", "clothing_dataset.csv")
        with open(dataset_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            rows.extend(reader)
        return rows

    def _ai_completion(self, system_prompt: str, user_prompt: str) -> str | None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None
        try:
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                    "input": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_output_tokens": 220,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            return payload.get("output", [{}])[0].get("content", [{}])[0].get("text")
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            return None

    def _shopping_search(self, query: str, location_label: str | None = None) -> list[dict]:
        api_key = os.environ.get("SERPAPI_API_KEY")
        if not api_key:
            return [
                {
                    "title": f"Search {query}",
                    "source": "Google Shopping India",
                    "price": "Search results",
                    "rating": None,
                    "reviews": None,
                    "thumbnail": None,
                    "link": f"https://www.google.com/search?tbm=shop&hl=en&gl=in&q={requests.utils.quote(query)}",
                },
                {
                    "title": f"Myntra search for {query}",
                    "source": "Myntra India",
                    "price": "Browse on Myntra",
                    "rating": None,
                    "reviews": None,
                    "thumbnail": None,
                    "link": f"https://www.google.com/search?tbm=shop&hl=en&gl=in&q={requests.utils.quote(query + ' Myntra')}",
                },
            ]
        try:
            response = requests.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_shopping_light",
                    "q": query,
                    "api_key": api_key,
                    "hl": "en",
                    "gl": "in",
                    "location": location_label or "India",
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("shopping_results", []) or payload.get("inline_shopping_results", [])
            items = []
            for result in results[:8]:
                items.append(
                    {
                        "title": result.get("title", "Product"),
                        "source": result.get("source", "Retailer"),
                        "price": result.get("price", "Price unavailable"),
                        "rating": result.get("rating"),
                        "reviews": result.get("reviews"),
                        "thumbnail": result.get("thumbnail"),
                        "link": result.get("product_link") or result.get("serpapi_product_api") or result.get("link"),
                    }
                )
            return items
        except (requests.RequestException, ValueError, TypeError):
            return []

    def _budget_phrase(self, budget: str) -> str:
        budget_key = str(budget).strip().lower()
        return {
            "500": "under INR 500",
            "1000": "under INR 1,000",
            "1k": "under INR 1,000",
            "2000": "under INR 2,000",
            "2k": "under INR 2,000",
            "5000+": "premium INR 5,000+",
            "5k+": "premium INR 5,000+",
        }.get(budget_key, "budget-friendly in India")

    def _india_marketplace_hint(self, budget: str) -> str:
        budget_key = str(budget).strip().lower()
        if budget_key in {"500", "1000", "1k"}:
            return "India retail Myntra Ajio Zudio"
        if budget_key in {"2000", "2k"}:
            return "India retail Myntra Ajio Tata CLiQ Westside"
        return "India luxury Myntra Tata CLiQ Luxe Ajio luxury H&M India"

    def _budget_style_hint(self, budget: str) -> str:
        budget_key = str(budget).strip().lower()
        if budget_key in {"500", "1000", "1k"}:
            return "affordable budget basics"
        if budget_key in {"2000", "2k"}:
            return "mid-range polished staples"
        return "premium elevated pieces"

    def _gender_search_hint(self, gender: str) -> str:
        normalized = (gender or "").strip().lower()
        if normalized in {"women", "woman", "female", "feminine"}:
            return "women's"
        if normalized in {"men", "man", "male", "masculine"}:
            return "men's"
        return "unisex"

    def _rank_products(self, piece_name: str, occasion: str, vibe: str, products: list[dict], budget: str = "") -> list[dict]:
        if not products:
            return []
        ai_pick = self._ai_completion(
            "You are a fashion commerce ranking assistant. Pick the 3 best products and return only their exact titles on separate lines.",
            (
                f"Piece: {piece_name}\nOccasion: {occasion}\nVibe: {vibe}\n"
                f"Products:\n" + "\n".join(
                    f"- {product['title']} | {product['source']} | {product['price']} | rating {product.get('rating')}"
                    for product in products
                )
            ),
        )
        if ai_pick:
            titles = {line.strip("- ").strip() for line in ai_pick.splitlines() if line.strip()}
            ranked = [product for product in products if product["title"] in titles]
            if ranked:
                return ranked[:3]
        return sorted(
            products,
            key=lambda product: (
                product.get("rating") or 0,
                product.get("reviews") or 0,
                1 if piece_name.lower() in product["title"].lower() else 0,
            ),
            reverse=True,
        )[:3]

    def _brief_keywords(self, brief: str) -> dict:
        text = brief.lower()
        return {
            "top": any(word in text for word in ["shirt", "tee", "t-shirt", "polo", "blouse", "jersey", "sweater", "hoodie", "knit"]),
            "bottom": any(word in text for word in ["trouser", "pant", "pants", "jean", "denim", "skirt", "short"]),
            "shoes": any(word in text for word in ["shoe", "sneaker", "boot", "loafer", "heel", "sandals"]),
            "outerwear": any(word in text for word in ["blazer", "jacket", "coat", "overshirt", "layer", "cardigan"]),
            "formal": any(word in text for word in ["formal", "wedding", "office", "work", "tailored", "dressy"]),
            "casual": any(word in text for word in ["casual", "relaxed", "street", "minimal", "laid back", "everyday"]),
            "bold": any(word in text for word in ["bold", "statement", "loud", "colorful", "bright"]),
            "neutral": any(word in text for word in ["neutral", "black", "white", "stone", "beige", "grey", "gray", "cream"]),
        }

    def _accessories_for_brief(self, brief: str, gender: str, dress_style: str, preferred_fabric: str) -> list[str]:
        text = brief.lower()
        tokens = [gender.lower(), dress_style.lower(), preferred_fabric.lower()]
        combined = " ".join(tokens)
        accessories = []
        if any(word in text or word in combined for word in ["formal", "office", "tailored", "dressy", "suit"]):
            accessories.extend(["Slim Watch", "Leather Belt"])
        if any(word in text or word in combined for word in ["street", "oversized", "casual", "relaxed", "minimal"]):
            accessories.extend(["Cap", "Crossbody Bag"])
        if any(word in text or word in combined for word in ["bold", "party", "statement", "colorful"]):
            accessories.extend(["Statement Ring", "Accent Sunglasses"])
        if any(word in text or word in combined for word in ["wedding", "event", "evening"]):
            accessories.extend(["Pocket Square", "Sleek Clutch"])
        if preferred_fabric and preferred_fabric.lower() in {"linen", "cotton", "silk", "wool", "denim"}:
            accessories.append(f"{preferred_fabric.title()} Scarf")
        if gender.lower() in {"women", "female", "feminine"}:
            accessories.append("Delicate Jewelry")
        elif gender.lower() in {"men", "male", "masculine"}:
            accessories.append("Minimal Watch")
        else:
            accessories.append("Versatile Layered Jewelry")
        deduped = []
        for accessory in accessories:
            if accessory not in deduped:
                deduped.append(accessory)
        return deduped[:4]

    def _score_wardrobe_item(self, item: dict, brief: str, weather: str, occasion: str, vibe: str, preferred_fabric: str = "", dress_style: str = "") -> int:
        text = brief.lower()
        score = 0
        if item["category"].lower() in text:
            score += 18
        if item["name"].lower() in text:
            score += 30
        if item["color"].lower() in text:
            score += 14
        if item["fabric"].lower() in text:
            score += 12
        if item["pattern"].lower() in text:
            score += 10
        if preferred_fabric and preferred_fabric.lower() == item["fabric"].lower():
            score += 16
        if dress_style and dress_style.lower() in item["occasion"].lower():
            score += 6
        if item["occasion"].lower() in text:
            score += 12
        if weather.lower() in item["season"].lower() or item["season"].lower() in weather.lower():
            score += 8
        if vibe.lower() in item["name"].lower() or vibe.lower() in item["fabric"].lower():
            score += 6
        if occasion.lower() in item["occasion"].lower():
            score += 10
        if item.get("favorite"):
            score += 5
        score += min(6, int(item.get("times_worn", 0) / 3))
        return score

    def _pick_piece(self, wardrobe: list[dict], category: str | tuple[str, ...], brief: str, weather: str, occasion: str, vibe: str, fallback: str, preferred_fabric: str = "", dress_style: str = "", budget: str = "") -> str:
        category_values = (category,) if isinstance(category, str) else category
        candidates = [item for item in wardrobe if item["category"].lower() in {value.lower() for value in category_values}]
        if not candidates:
            return self._generated_piece(brief, category_values[0], weather, vibe, budget=budget)
        best = max(candidates, key=lambda item: self._score_wardrobe_item(item, brief, weather, occasion, vibe, preferred_fabric, dress_style))
        best_score = self._score_wardrobe_item(best, brief, weather, occasion, vibe, preferred_fabric, dress_style)
        if best_score < 28 and brief.strip():
            return self._generated_piece(brief, category_values[0], weather, vibe, budget=budget)
        return best["name"]

    def _generated_piece(self, brief: str, category: str, weather: str, vibe: str, budget: str = "") -> str:
        text = brief.lower()
        color = "Black" if "black" in text else "White" if "white" in text else "Stone" if "stone" in text or "beige" in text else "Navy" if "navy" in text else "Neutral"
        budget_key = str(budget).strip().lower()
        budget_tag = "Core" if budget_key in {"500", "1000", "1k"} else "Balanced" if budget_key in {"2000", "2k"} else "Premium"
        if category.lower() == "top":
            if any(word in text for word in ["shirt", "dress shirt", "button"]):
                return f"{color} {budget_tag} Shirt"
            if any(word in text for word in ["polo", "knit"]):
                return f"{color} {budget_tag} Knit Polo"
            if any(word in text for word in ["jersey", "sport", "athletic"]):
                return f"{color} {budget_tag} Jersey"
            return f"{color} {budget_tag} Tee"
        if category.lower() == "bottom":
            if any(word in text for word in ["jean", "denim"]):
                return f"{color} {budget_tag} Jean"
            if any(word in text for word in ["skirt"]):
                return f"{color} {budget_tag} Skirt"
            return f"{color} {budget_tag} Trouser"
        if category.lower() == "shoes":
            if any(word in text for word in ["boot", "chelsea"]):
                return f"{color} {budget_tag} Boot"
            if any(word in text for word in ["loafer"]):
                return f"{color} {budget_tag} Loafer"
            return f"{color} {budget_tag} Sneaker"
        if category.lower() in {"outerwear", "blazer"}:
            if weather.lower() == "rainy":
                return f"{color} {budget_tag} Jacket"
            if weather.lower() == "cold":
                return f"{color} {budget_tag} Coat"
            return f"{color} {budget_tag} Layer"
        return f"{color} {budget_tag} Accessory"

    def _compose_brief_outfit(self, user_id: int, wardrobe: list[dict], brief: str, weather: str, occasion: str, vibe: str, temperature: int, gender: str, preferred_fabric: str, dress_style: str, budget: str) -> dict:
        keywords = self._brief_keywords(brief)
        selected_top = self._pick_piece(wardrobe, "Top", brief, weather, occasion, vibe, "Relaxed Tee", preferred_fabric, dress_style, budget=budget)
        selected_bottom = self._pick_piece(wardrobe, "Bottom", brief, weather, occasion, vibe, "Wide Leg Trouser", preferred_fabric, dress_style, budget=budget)
        selected_shoes = self._pick_piece(wardrobe, "Shoes", brief, weather, occasion, vibe, "Minimal Sneaker", preferred_fabric, dress_style, budget=budget)
        selected_layer = self._pick_piece(wardrobe, ("Outerwear", "Blazer"), brief, weather, occasion, vibe, "Light Layer", preferred_fabric, dress_style, budget=budget)

        if keywords["outerwear"] and selected_layer == "Light Layer":
            selected_layer = "Tailored Overshirt"
        if keywords["formal"]:
            selected_top = selected_top if selected_top != "Relaxed Tee" else "Crisp Dress Shirt"
            selected_bottom = selected_bottom if selected_bottom != "Wide Leg Trouser" else "Tailored Trouser"
            selected_shoes = selected_shoes if selected_shoes != "Minimal Sneaker" else "Oxford Shoes"
        elif keywords["casual"] and selected_top == "Relaxed Tee":
            selected_top = "Easy Cotton Tee"
        if weather.lower() == "rainy" and "Water-resistant" not in selected_layer:
            selected_layer = "Water-resistant Layer"
        elif weather.lower() == "hot" and "Linen" not in selected_layer:
            selected_layer = "Breathable Linen Layer"
        elif temperature < 18 and "Jacket" not in selected_layer and "Layer" not in selected_layer:
            selected_layer = "Light Jacket"

        accessories = self._accessories_for_brief(brief, gender, dress_style, preferred_fabric)
        budget_phrase = self._budget_phrase(budget)

        compatibility = 78
        compatibility += 6 if keywords["formal"] else 0
        compatibility += 4 if keywords["neutral"] else 0
        compatibility += 3 if keywords["bold"] else 0
        compatibility = min(98, compatibility + min(8, len(brief.split()) // 2))

        ai_reasoning = self._ai_completion(
            "You are a precise fashion stylist. Reply with 2 short sentences that reflect the user's style brief.",
            (
                f"Style brief: {brief}. Weather: {weather}. Occasion: {occasion}. Vibe: {vibe}. "
                f"Selected outfit: top {selected_top}, bottom {selected_bottom}, shoes {selected_shoes}, layer {selected_layer}."
            ),
        )
        if not ai_reasoning:
            ai_reasoning = (
                f"The brief '{brief}' is being translated into a cleaner, more specific outfit instead of a repeated default look. "
                f"I kept the palette and layers aligned to {weather.lower()} weather and a {vibe.lower()} finish."
            )

        name_seed = " ".join(word.strip(",.?!") for word in brief.split()[:4]).strip()
        outfit_name = name_seed.title() if name_seed else f"{occasion} {vibe} Edit"
        saved = self.store.save_outfit(
            user_id=user_id,
            outfit={
                "name": outfit_name,
                "occasion": occasion,
                "weather": weather,
                "mood": vibe,
                "items": [selected_top, selected_bottom, selected_shoes, selected_layer, *accessories],
                "style_request": brief,
                "score": compatibility,
                "liked": compatibility > 85,
                "date": "2026-04-09",
            },
        )
        return {
            "summary": f"Your brief '{brief}' shaped this outfit into a more personal, saved look.",
            "style_personality": self.store.get_state(user_id)["user_profile"]["style_personality"],
            "style_dna": self.store.get_state(user_id)["user_profile"]["style_dna"],
            "recommendation": {
                "top": selected_top,
                "bottom": selected_bottom,
                "shoes": selected_shoes,
                "layer": selected_layer,
                "accessories": accessories,
            },
            "occasion": occasion,
            "weather": weather,
            "temperature": temperature,
            "vibe": vibe,
            "gender": gender,
            "preferred_fabric": preferred_fabric,
            "dress_style": dress_style,
            "compatibility_score": compatibility,
            "outfit_reasoning": ai_reasoning,
            "capsule_builder": [
                "Core top with better fit match",
                "Tonal bottom for balance",
                "Clean shoe anchor",
                "Weather-aware outer layer",
            ],
            "wardrobe_gap": "A second interchangeable top would make the timeline more varied.",
            "shopping_recommendation": "Use the brief-driven outfit as the base and swap in similar pieces from the web when available.",
            "web_outfit_suggestions": self._web_outfit_recommendations(
                {
                    "top": selected_top,
                    "bottom": selected_bottom,
                    "shoes": selected_shoes,
                },
                occasion,
                vibe,
                gender=gender,
                location_label=None,
                style_request=brief,
                budget=budget,
            ),
            "daily_suggestion": f"Today's saved style idea is '{brief}' with a {vibe.lower()} finish.",
            "saved_outfit": saved,
            "style_request": brief,
            "accessories": accessories,
            "budget": budget,
            "budget_phrase": budget_phrase,
        }

    def _web_outfit_recommendations(
        self,
        recommendation: dict,
        occasion: str,
        vibe: str,
        gender: str = "",
        location_label: str | None = None,
        style_request: str | None = None,
        budget: str | None = None,
    ) -> list[dict]:
        search_map = [
            ("Top", recommendation["top"]),
            ("Bottom", recommendation["bottom"]),
            ("Shoes", recommendation["shoes"]),
        ]
        budget_phrase = self._budget_phrase(budget or "")
        marketplace_hint = self._india_marketplace_hint(budget or "")
        budget_style_hint = self._budget_style_hint(budget or "")
        gender_hint = self._gender_search_hint(gender)
        web_results = []
        for category, piece in search_map:
            if style_request:
                query = f"{gender_hint} {style_request} {category.lower()} outfit {occasion} {vibe} fashion {budget_phrase} {budget_style_hint} {marketplace_hint}"
            else:
                query = f"{gender_hint} {piece} {occasion} {vibe} fashion {budget_phrase} {budget_style_hint} {marketplace_hint}"
            products = self._shopping_search(query, location_label=location_label)
            web_results.append(
                {
                    "category": category,
                    "piece": piece,
                    "products": self._rank_products(piece, occasion, vibe, products, budget=budget or ""),
                }
            )
        return web_results

    def get_platform_summary(self, user_id: int) -> dict:
        state = self.store.get_state(user_id)
        wardrobe = state["wardrobe_items"]
        outfits = state["outfit_history"]
        favorites = [item for item in wardrobe if item.get("favorite")]
        return {
            "hero_metrics": [
                {"label": "Wardrobe Pieces", "value": len(wardrobe)},
                {"label": "Saved Looks", "value": len(outfits)},
                {"label": "Favorites", "value": len(favorites)},
                {"label": "AI Confidence", "value": "94%"},
            ],
            "feature_groups": [
                {
                    "title": "Core AI Styling",
                    "items": [
                        "Weather-aware outfit recommendations",
                        "Occasion-based outfit generation",
                        "Daily AI stylist suggestions",
                        "Style DNA profiling",
                    ],
                },
                {
                    "title": "Virtual Try-On",
                    "items": [
                        "Avatar-based try-on",
                        "Multi-garment overlays",
                        "Body-type fit simulation",
                        "Alignment and resize notes",
                    ],
                },
                {
                    "title": "Smart Wardrobe",
                    "items": [
                        "Automatic clothing tagging",
                        "Outfit history tracking",
                        "Wardrobe insights",
                        "Capsule wardrobe planning",
                    ],
                },
            ],
            "profile": state["user_profile"],
            "community_feed": state["community_feed"],
        }

    def recommend(self, user_id: int, payload: dict) -> dict:
        state = self.store.get_state(user_id)
        wardrobe = state["wardrobe_items"]
        profile = state["user_profile"]

        weather = payload.get("weather", "Warm")
        occasion = payload.get("occasion", "Casual")
        vibe = payload.get("vibe", "Polished")
        temperature = int(payload.get("temperature", 28))
        style_request = (payload.get("style_request") or payload.get("brief") or payload.get("opinion") or "").strip()
        gender = (payload.get("gender") or payload.get("user_gender") or "Unspecified").strip()
        preferred_fabric = (payload.get("preferred_fabric") or payload.get("fabric") or "Cotton").strip()
        dress_style = (payload.get("dress_style") or payload.get("preferred_style") or payload.get("style_of_dress") or occasion).strip()
        budget = (payload.get("budget") or "1000").strip()
        reference_image_url = (payload.get("reference_image_url") or "").strip()
        reference_image_name = (payload.get("reference_image_name") or "").strip()
        image_hint = (payload.get("image_hint") or "").strip()
        visual_anchor = image_hint or reference_image_name or "reference image"

        if reference_image_url or reference_image_name or image_hint:
            style_request = " ".join(
                part
                for part in [
                    style_request,
                    f"inspired by {visual_anchor}",
                ]
                if part
            ).strip()

        if style_request:
            result = self._compose_brief_outfit(user_id, wardrobe, style_request, weather, occasion, vibe, temperature, gender, preferred_fabric, dress_style, budget)
            result["reference_image_url"] = reference_image_url or None
            result["reference_image_name"] = reference_image_name or None
            result["image_inspired_note"] = (
                "AI stylist used your uploaded image to steer the outfit."
                if reference_image_url
                else "AI stylist used your text inputs to steer the outfit."
            )
            return result

        tops = [item for item in wardrobe if item["category"] == "Top"]
        bottoms = [item for item in wardrobe if item["category"] == "Bottom"]
        shoes = [item for item in wardrobe if item["category"] == "Shoes"]
        outerwear = [item for item in wardrobe if item["category"] in {"Outerwear", "Blazer"}]

        selected_top = tops[0]["name"] if tops else "Relaxed Tee"
        selected_bottom = bottoms[0]["name"] if bottoms else "Wide Leg Trouser"
        selected_shoes = shoes[0]["name"] if shoes else "Minimal Sneaker"
        selected_layer = outerwear[0]["name"] if temperature < 22 and outerwear else "No extra layer"

        if occasion.lower() == "formal":
            selected_top = "White Dress Shirt"
            selected_bottom = "Tailored Pleated Trouser"
            selected_shoes = "Oxford Shoes"
        elif occasion.lower() == "party":
            selected_top = "Textured Knit Polo"
            selected_bottom = "Slim Black Trouser"
            selected_shoes = "Leather Chelsea Boots"

        if weather.lower() == "rainy":
            selected_layer = "Water-resistant overshirt"
        elif weather.lower() == "hot":
            selected_layer = "Breathable linen overshirt"

        palette = profile["preferred_palette"]
        compatibility = min(98, 76 + len(palette) + len(vibe))
        accessories = self._accessories_for_brief(f"{weather} {occasion} {vibe} {style_request}".strip(), gender, dress_style, preferred_fabric)
        capsule = [
            "Relaxed blazer",
            "Premium white tee",
            "Straight denim",
            "Leather sneaker",
            "Lightweight knit polo",
        ]
        wardrobe_gap = "A versatile mid-layer jacket would unlock more rainy-day and travel looks."
        insight = (
            f"{profile['style_personality']} energy works best here: keep the base clean, "
            f"let {vibe.lower()} texture lead, and anchor the look with {palette[1].lower()}."
        )

        ai_reasoning = self._ai_completion(
            "You are an expert AI fashion stylist. Respond with 2 concise sentences.",
            (
                f"Create outfit reasoning for a user with style personality {profile['style_personality']}, "
                f"weather {weather}, occasion {occasion}, vibe {vibe}, palette {', '.join(palette)}."
            ),
        )
        saved = self.store.save_outfit(
            user_id,
            {
                "name": f"{occasion} {vibe} Edit",
                "occasion": occasion,
                "weather": weather,
                "mood": vibe,
                "items": [selected_top, selected_bottom, selected_shoes, selected_layer, *accessories],
                "style_request": style_request,
                "score": compatibility,
                "liked": compatibility > 85,
                "date": "2026-04-09",
            }
        )
        accessories = self._accessories_for_brief(f"{weather} {occasion} {vibe} {style_request}".strip(), gender, dress_style, preferred_fabric)
        budget_phrase = self._budget_phrase(budget)

        return {
            "summary": f"{weather} weather and a {occasion.lower()} plan call for breathable structure with polished balance.",
            "style_personality": profile["style_personality"],
            "style_dna": profile["style_dna"],
            "recommendation": {
                "top": selected_top,
                "bottom": selected_bottom,
                "shoes": selected_shoes,
                "layer": selected_layer,
                "accessories": accessories,
            },
            "occasion": occasion,
            "weather": weather,
            "temperature": temperature,
            "vibe": vibe,
            "gender": gender,
            "preferred_fabric": preferred_fabric,
            "dress_style": dress_style,
            "budget": budget,
            "budget_phrase": budget_phrase,
            "compatibility_score": compatibility,
            "outfit_reasoning": ai_reasoning or insight,
            "capsule_builder": capsule,
            "wardrobe_gap": wardrobe_gap,
            "shopping_recommendation": "Add a lightweight water-resistant jacket and a deep olive trouser for more outfit combinations.",
            "web_outfit_suggestions": self._web_outfit_recommendations(
                {
                    "top": selected_top,
                    "bottom": selected_bottom,
                    "shoes": selected_shoes,
                },
                occasion,
                vibe,
                gender=gender,
                location_label=payload.get("location_label"),
                style_request=style_request or None,
                budget=budget,
            ),
            "daily_suggestion": "Tomorrow's AI daily look: knit polo, cropped trouser, retro sneaker, and a minimalist watch.",
            "saved_outfit": saved,
            "style_request": style_request,
            "accessories": accessories,
            "reference_image_url": reference_image_url or None,
            "reference_image_name": reference_image_name or None,
            "image_inspired_note": (
                "AI stylist used your uploaded image to steer the outfit."
                if reference_image_url
                else "AI stylist used your text inputs to steer the outfit."
            ),
        }

    def weather_report_outfit(self, user_id: int, payload: dict) -> dict:
        weather = {
            "city": payload.get("city", "Your area"),
            "country": payload.get("country", ""),
            "description": payload.get("description", payload.get("weather", "Current local weather")),
            "temperature": int(payload.get("temperature", 27)),
            "feels_like": int(payload.get("feels_like", payload.get("temperature", 27))),
            "weather_label": payload.get("weather", "Warm"),
            "location_label": payload.get("location_label", "Location shared"),
        }
        occasion = "Work" if weather["weather_label"] in {"Mild", "Cold"} else "Casual"
        vibe = "Minimal" if weather["weather_label"] in {"Warm", "Hot"} else "Polished"
        recommendation = self.recommend(
            user_id,
            {
                "weather": weather["weather_label"],
                "occasion": occasion,
                "vibe": vibe,
                "temperature": weather["temperature"],
            },
        )
        recommendation["weather_report"] = weather
        recommendation["notification"] = (
            f"{weather['location_label']}: {weather['description']}, {weather['temperature']}C. "
            f"Suggested look: {recommendation['recommendation']['top']} with {recommendation['recommendation']['bottom']}."
        )
        return recommendation

    def chat(self, user_id: int, payload: dict) -> dict:
        message = (payload.get("message") or "").strip().lower()
        state = self.store.get_state(user_id)
        profile = state["user_profile"]
        ai_reply = self._ai_completion(
            "You are a warm fashion stylist assistant. Reply in 2 short sentences.",
            (
                f"User style personality: {profile['style_personality']}. "
                f"Preferred palette: {', '.join(profile['preferred_palette'])}. "
                f"Question: {payload.get('message', '')}"
            ),
        )
        if "wedding" in message:
            reply = "Choose soft tailoring, a crisp shirt, and low-contrast accessories so the outfit feels elevated without stealing focus."
        elif "office" in message:
            reply = "Aim for one structured piece, one relaxed piece, and one polished shoe to keep the office look modern."
        elif "vacation" in message or "beach" in message:
            reply = "Lean into open-weave fabrics, airy layers, and a pale color palette that photographs well in sunlight."
        else:
            reply = "Build the outfit around one hero piece, keep the palette tight, and balance texture against clean silhouettes."
        return {
            "reply": ai_reply or reply,
            "memory": [
                "Prefers soft neutrals",
                "Usually selects clean sneakers",
                "Responds well to polished-casual layering",
            ],
        }

    def try_on(self, user_id: int, payload: dict) -> dict:
        top = payload.get("top", "Knit Polo")
        bottom = payload.get("bottom", "Tailored Trouser")
        avatar = payload.get("avatar", "City Muse")
        body_type = payload.get("body_type", "Athletic")
        fit = payload.get("fit", "True to size")
        height_cm = int(payload.get("height_cm", 172))
        shoulder_cm = int(payload.get("shoulder_cm", 46))
        waist_cm = int(payload.get("waist_cm", 80))
        inseam_cm = int(payload.get("inseam_cm", 78))
        distance = payload.get("camera_distance", "Medium")
        posture = payload.get("posture", "Neutral")
        frame_width = max(320, int(payload.get("frame_width", 720)))
        frame_height = max(480, int(payload.get("frame_height", 960)))

        distance_scale = {
            "Close": 1.08,
            "Medium": 1.0,
            "Far": 0.9,
        }.get(distance, 1.0)
        posture_shift = {
            "Neutral": 0,
            "Relaxed": 10,
            "Straight": -8,
        }.get(posture, 0)
        top_width = round(min(68, max(34, (shoulder_cm / 1.35) * distance_scale)))
        top_height = round(min(42, max(28, (height_cm * 0.19) * distance_scale / 2.4)))
        bottom_width = round(min(58, max(28, (waist_cm / 1.8) * distance_scale)))
        bottom_height = round(min(52, max(30, (inseam_cm / 1.45) * distance_scale / 2.0)))
        shoulder_line = round(max(18, min(28, 22 + ((shoulder_cm - 44) * 0.35))))
        waist_line = round(max(44, min(60, 49 + ((inseam_cm - 76) * 0.18))) + posture_shift / 4)
        fit_balance = round(
            max(
                72,
                min(
                    96,
                    88
                    - abs(shoulder_cm - 46) * 0.45
                    - abs(waist_cm - 80) * 0.18
                    - (6 if fit == "Tailored fit" and posture == "Relaxed" else 0)
                    + (3 if distance == "Medium" else 0),
                ),
            )
        )

        return {
            "avatar": avatar,
            "preview_layers": [
                {"name": top, "position": "upper body", "alignment": "centered with shoulder match"},
                {"name": bottom, "position": "lower body", "alignment": "waist aligned with slight taper"},
            ],
            "fit_notes": [
                f"{body_type} frame benefits from a lightly defined waist and relaxed shoulder line.",
                f"Recommended fit mode: {fit}. Camera distance is set to {distance.lower()} with {posture.lower()} posture compensation.",
                f"Calibration uses {height_cm} cm height, {shoulder_cm} cm shoulder span, and {waist_cm} cm waist width for overlay sizing.",
            ],
            "simulation": {
                "overlay_quality": "Calibrated live preview",
                "body_map_confidence": f"{fit_balance}%",
                "multi_garment_mode": True,
                "real_time_preview": True,
            },
            "overlay_layout": {
                "frame": {"width": frame_width, "height": frame_height},
                "guides": {
                    "shoulder_line": shoulder_line,
                    "waist_line": waist_line,
                    "center_line": 50,
                },
                "top": {
                    "x": round(50 - (top_width / 2), 1),
                    "y": round(max(14, shoulder_line - 2), 1),
                    "width": top_width,
                    "height": top_height,
                    "label": top,
                },
                "bottom": {
                    "x": round(50 - (bottom_width / 2), 1),
                    "y": round(waist_line, 1),
                    "width": bottom_width,
                    "height": bottom_height,
                    "label": bottom,
                },
            },
            "calibration": {
                "fit_balance": fit_balance,
                "distance": distance,
                "posture": posture,
                "recommended_actions": [
                    "Keep shoulders inside the top guide for the cleanest alignment.",
                    "Stand 1.5 to 2 meters from the camera for full-body framing.",
                    "Use neutral posture and even lighting to improve overlay consistency.",
                ],
            },
        }

    def discover(self, user_id: int, payload: dict) -> dict:
        query = (payload.get("query") or "minimal").lower()
        state = self.store.get_state(user_id)
        matches = []
        for entry in state["community_feed"]:
            searchable = " ".join([entry["title"], entry["style"], entry["trend"]]).lower()
            if query in searchable or query == "minimal":
                matches.append(entry)
        if not matches:
            matches = state["community_feed"][:2]
        return {
            "query": query,
            "results": matches,
            "trending_tags": ["quiet luxury", "utility layering", "vacation minimal", "tailored monochrome"],
            "visual_search_note": "Visual search is currently represented by style-tag matching and curated inspiration results.",
        }

    def generate_lookbook(self, user_id: int, payload: dict) -> dict:
        theme = payload.get("theme", "City Weekend")
        state = self.store.get_state(user_id)
        profile = state["user_profile"]
        ai_note = self._ai_completion(
            "You create fashion lookbook concepts. Return exactly 3 short look descriptions separated by new lines.",
            f"Theme: {theme}. Style personality: {profile['style_personality']}. Palette: {', '.join(profile['preferred_palette'])}.",
        )
        looks = [
            {"title": "Arrival Look", "description": "Relaxed shirt, clean trouser, leather sneaker."},
            {"title": "Gallery Look", "description": "Knit polo, pleated trouser, soft blazer."},
            {"title": "Night Look", "description": "Monochrome shirt, dark trouser, sleek boot."},
        ]
        if ai_note:
            ai_lines = [line.strip("- ").strip() for line in ai_note.splitlines() if line.strip()]
            looks = [
                {"title": f"Look {index + 1}", "description": line}
                for index, line in enumerate(ai_lines[:3])
            ] or looks
        return {
            "theme": theme,
            "looks": looks,
            "image_generation_note": "If OPENAI_API_KEY is set, lookbook concepts are generated live. Otherwise this uses local curated prompts.",
        }

    def analytics(self, user_id: int) -> dict:
        state = self.store.get_state(user_id)
        wardrobe = state["wardrobe_items"]
        outfits = state["outfit_history"]

        color_counts = Counter(item["color"] for item in wardrobe)
        category_counts = Counter(item["category"] for item in wardrobe)
        avg_score = round(mean(entry["score"] for entry in outfits), 1) if outfits else 0
        top_worn = sorted(wardrobe, key=lambda item: item.get("times_worn", 0), reverse=True)[:3]

        return {
            "statistics": [
                {"label": "Average Outfit Score", "value": avg_score},
                {"label": "Most Worn Piece", "value": top_worn[0]["name"] if top_worn else "N/A"},
                {"label": "Favorite Color", "value": color_counts.most_common(1)[0][0] if color_counts else "N/A"},
                {"label": "Top Category", "value": category_counts.most_common(1)[0][0] if category_counts else "N/A"},
            ],
            "usage": [{"name": item["name"], "wears": item.get("times_worn", 0)} for item in top_worn],
            "category_breakdown": [{"name": name, "count": count} for name, count in category_counts.items()],
            "color_breakdown": [{"name": name, "count": count} for name, count in color_counts.items()],
            "timeline": outfits[:6],
            "insights": [
                "Your wardrobe leans polished-casual with strong neutral foundations.",
                "Adding one statement accessory category would improve outfit variety.",
                "Saved looks perform best when a soft textured top is paired with a tailored bottom.",
            ],
        }
