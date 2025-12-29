"""Content prioritization system for weather narratives

This module handles prioritizing and selecting content components for weather narratives
to maximize useful information while staying within display constraints.
"""

import re


class ContentItem:
    """Represents a piece of content with priority and text alternatives"""

    def __init__(self, text, priority=5, short_text=None, category="general"):
        self.text = text
        self.priority = priority  # Higher numbers = more important (like CSS z-index)
        self.short_text = short_text or text
        self.category = category
        self.length = len(text)
        self.short_length = len(self.short_text)

    def get_best_text(self, max_length=None):
        """Get the best text variant that fits within max_length"""
        if max_length is None:
            return self.text

        if self.length <= max_length:
            return self.text
        elif self.short_length <= max_length:
            return self.short_text
        else:
            return None  # Can't fit


class ContentPrioritizer:
    """Prioritizes and optimizes content for weather narratives"""

    def __init__(self, max_length=400, max_lines=7):
        self.max_length = max_length
        self.max_lines = max_lines
        self.content_items = []
        self.text_alternatives = self._get_text_alternatives()
        self.use_short_format = False

    def _strip_formatting_tags(self, text):
        """Strip all formatting tags to get clean text content"""
        return re.sub(r"<[^>]+>", "", text)

    def add_item(self, text, priority=5, short_text=None, category="general"):
        """Add a content item to be prioritized"""
        item = ContentItem(text, priority, short_text, category)
        self.content_items.append(item)

    def add_items(self, items):
        """Add multiple content items from a list of dicts"""
        for item_data in items:
            if isinstance(item_data, dict):
                self.add_item(
                    text=item_data.get("text", ""),
                    priority=item_data.get("priority", 5),
                    short_text=item_data.get("short_text"),
                    category=item_data.get("category", "general"),
                )
            elif isinstance(item_data, str):
                self.add_item(item_data)

    def optimize_narrative(self):
        """Generate optimized narrative within constraints

        Returns:
            str: Optimized narrative text
        """
        if not self.content_items:
            return ""

        # Sort by priority (highest first)
        sorted_items = sorted(
            self.content_items, key=lambda x: x.priority, reverse=True
        )

        # Try to fit as much high-priority content as possible
        selected_texts = []
        total_length = 0

        for item in sorted_items:
            # Try full text first
            candidate_text = item.text
            candidate_length = len(candidate_text)

            # Check if adding this item would exceed limits
            test_length = total_length + candidate_length
            if selected_texts:
                test_length += 2  # Account for ". " separator

            if test_length <= self.max_length:
                selected_texts.append(candidate_text)
                total_length = test_length
            else:
                # Try short text
                candidate_text = item.short_text
                candidate_length = len(candidate_text)
                test_length = total_length + candidate_length
                if selected_texts:
                    test_length += 2

                if test_length <= self.max_length:
                    selected_texts.append(candidate_text)
                    total_length = test_length
                # If short text doesn't fit either, skip this item

        # Try progressive optimization - first with long format, then short
        for use_short in [False, True]:
            self.use_short_format = use_short
            selected_by_category = self._select_from_categories(sorted_items)

            if not selected_by_category:
                continue

            # Build narrative with current format setting
            narrative = self._build_narrative_with_length_check(selected_by_category)

            if len(narrative) <= self.max_length:
                return narrative

        # If still too long after short format, truncate
        return self._smart_truncate(narrative) if narrative else ""

    def _build_narrative_with_length_check(self, items):
        """Build narrative checking length at each step"""
        narrative_parts = []

        for item in items:
            # Choose text based on current format setting and available space
            text_to_use = self._choose_text_variant(item, narrative_parts)

            if text_to_use:
                narrative_parts.append(text_to_use)

        if not narrative_parts:
            return ""

        # Join with smart punctuation and apply format-specific alternatives
        narrative = self._smart_join_parts(narrative_parts)

        if self.use_short_format:
            narrative = self._apply_text_alternatives(narrative)

        return narrative

    def _choose_text_variant(self, item, current_parts):
        """Choose appropriate text variant based on space constraints"""
        # Calculate current length
        current_length = sum(len(part) for part in current_parts)
        if current_parts:
            current_length += (
                len(". ") * (len(current_parts) - 1) + 2
            )  # separators + punct

        remaining_space = self.max_length - current_length

        # Choose text variant
        if self.use_short_format and item.short_text:
            candidate_text = item.short_text
        else:
            candidate_text = item.text

        # Check if it fits
        if len(candidate_text) <= remaining_space:
            return candidate_text
        elif item.short_text and len(item.short_text) <= remaining_space:
            return item.short_text
        else:
            return None  # Skip this item

    def _select_from_categories(self, sorted_items):
        """Select one item from each category, prioritizing by importance"""
        category_items = {}

        for item in sorted_items:
            category = item.category
            if category not in category_items:
                category_items[category] = []
            category_items[category].append(item)

        # For suggestion categories, pick one randomly from top priority items
        selected_items = []

        for category, items in category_items.items():
            if category in ["weather_suggestion", "seasonal", "general"]:
                # For suggestions, pick one from the highest priority items
                if items:
                    max_priority = max(item.priority for item in items)
                    top_items = [
                        item for item in items if item.priority == max_priority
                    ]

                    # Simple pseudo-random selection based on text length
                    selected = top_items[len(top_items[0].text) % len(top_items)]
                    selected_items.append(selected)
            else:
                # For other categories (current, tomorrow, etc.), include all
                selected_items.extend(items)

        # Re-sort by priority
        return sorted(selected_items, key=lambda x: x.priority, reverse=True)

    def _smart_join_parts(self, parts):
        """Join text parts with smart punctuation handling"""
        if not parts:
            return ""

        if len(parts) == 1:
            text = parts[0]
            clean_text = self._strip_formatting_tags(text)
            if clean_text and not clean_text.rstrip().endswith((".", "!", "?")):
                return text + "."
            return text

        # Join multiple parts
        result = parts[0]
        for part in parts[1:]:
            # Check if previous part already ends with punctuation
            clean_previous = self._strip_formatting_tags(result).rstrip()
            if clean_previous.endswith((".", "!", "?")):
                result += f" {part}"
            else:
                result += f". {part}"

        # Ensure final punctuation
        clean_final = self._strip_formatting_tags(result).rstrip()
        if not clean_final.endswith((".", "!", "?")):
            result += "."

        return result

    def _apply_text_alternatives(self, text):
        """Apply text alternatives to shorten the narrative"""
        for long_form, short_form in self.text_alternatives.items():
            text = text.replace(long_form, short_form)

        return text

    def _smart_truncate(self, text):
        """Intelligently truncate text to fit constraints"""
        if len(text) <= self.max_length:
            return text

        # Try to truncate at sentence boundaries
        sentences = text.split(". ")
        truncated = sentences[0]

        for sentence in sentences[1:]:
            test_length = len(truncated + ". " + sentence)
            if test_length <= self.max_length:
                truncated += ". " + sentence
            else:
                break

        # If still too long, truncate the last sentence
        if len(truncated) > self.max_length:
            truncated = truncated[: self.max_length - 3] + "..."

        return truncated

    def get_priority_stats(self):
        """Get statistics about content priorities"""
        if not self.content_items:
            return {}

        priorities = [item.priority for item in self.content_items]
        categories = {}

        for item in self.content_items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item.priority)

        return {
            "total_items": len(self.content_items),
            "min_priority": min(priorities),
            "max_priority": max(priorities),
            "avg_priority": sum(priorities) / len(priorities),
            "categories": {
                cat: {"count": len(prios), "avg_priority": sum(prios) / len(prios)}
                for cat, prios in categories.items()
            },
        }

    def _get_text_alternatives(self):
        """Get dictionary of text alternatives for shortening"""
        return {
            "Tomorrow": "Tmrrw",
            "tomorrow": "tmrrw",
            "expected": "exp",
            "around": "~",
            "afternoon": "PM",
            "morning": "AM",
            "evening": "eve",
            "overnight": "o/n",
            "currently": "now",
            "likely": "prob",
            "possible": "poss",
            "thunderstorms": "t-storms",
            "Thunderstorms": "T-storms",
            "precipitation": "precip",
            "temperature": "temp",
            "New moon tonight.": "New moon!",
            "Full moon tonight.": "Full moon!",
            "clearing": "clear",
            "starting": "start",
            "expected to": "exp to",
            "feels like": "feels",
            "due to wind": "wind",
            "due to humidity": "humid",
            "wind gusts": "gusts",
        }


def create_prioritized_narrative(content_parts, max_length=400):
    """Convenience function to create a prioritized narrative from content parts

    Args:
        content_parts: List of content items (dicts or ContentItem objects)
        max_length: Maximum length for the narrative

    Returns:
        str: Optimized narrative
    """
    prioritizer = ContentPrioritizer(max_length=max_length)

    for part in content_parts:
        if isinstance(part, ContentItem):
            prioritizer.content_items.append(part)
        elif isinstance(part, dict):
            prioritizer.add_item(
                text=part.get("text", ""),
                priority=part.get("priority", 5),
                short_text=part.get("short_text"),
                category=part.get("category", "general"),
            )
        elif isinstance(part, str):
            prioritizer.add_item(part)

    return prioritizer.optimize_narrative()
