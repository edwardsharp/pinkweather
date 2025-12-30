"""Content prioritization system for weather narratives

This module handles prioritizing and selecting content components for weather narratives
to maximize useful information while staying within display constraints.
"""

import re

from utils.logger import log


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
        self._text_renderer = None
        self._setup_text_renderer()

    def _setup_text_renderer(self):
        """Initialize text renderer for accurate line counting"""
        try:
            from display.text_renderer import TextRenderer

            self._text_renderer = TextRenderer()
            log("Text renderer initialized for content prioritizer")
        except Exception as e:
            log(f"Failed to initialize text renderer: {e}")
            self._text_renderer = None

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

        # Use iterative optimization to maximize space utilization
        return self._optimize_narrative_iteratively(sorted_items)

    def _optimize_narrative_iteratively(self, sorted_items):
        """Try multiple combinations to maximize space utilization"""
        log(f"Starting iterative optimization with {len(sorted_items)} content items")
        best_narrative = ""
        best_line_count = 0

        # Try up to 5 different combinations
        for attempt in range(5):
            try:
                # Try different combinations of content
                candidate_content = self._try_combination(sorted_items, attempt)
                candidate_narrative = self._smart_join_parts(candidate_content)

                # Measure actual line count
                line_count = self._get_actual_line_count(candidate_narrative)

                log(
                    f"Attempt {attempt}: {len(candidate_content)} items, {line_count} lines, {len(candidate_narrative)} chars"
                )

                # Keep if it fits and is better than what we have
                if line_count <= self.max_lines and line_count > best_line_count:
                    best_narrative = candidate_narrative
                    best_line_count = line_count
                    log(f"New best: {best_line_count} lines")

                # Perfect fit - stop trying
                if line_count == self.max_lines:
                    log(f"Perfect fit found on attempt {attempt}!")
                    break

            except Exception as e:
                log(f"Attempt {attempt} failed: {e}")
                continue

        # Fallback to original algorithm if iterative optimization fails
        if not best_narrative:
            log("Iterative optimization failed, using fallback")
            best_narrative = self._fallback_optimize(sorted_items)
        else:
            log(f"Final optimized narrative: {best_line_count} lines")

        return best_narrative

    def _try_combination(self, sorted_items, attempt):
        """Try different combinations of content based on attempt number"""
        # Attempt 0: Core high-priority content only
        # Attempt 1: Core + time-based content
        # Attempt 2: Core + activity suggestions
        # Attempt 3: Core + multiple lower-priority categories
        # Attempt 4: Use short text variants for more content

        if attempt == 0:
            # Just core content (priority 6+)
            return [item for item in sorted_items if item.priority >= 6]

        elif attempt == 1:
            # Core + time-based/greeting content (priority 4-5)
            core_items = [item for item in sorted_items if item.priority >= 6]
            time_items = [
                item
                for item in sorted_items
                if 4 <= item.priority < 6
                and any(
                    word in item.text.lower()
                    for word in ["morning", "evening", "afternoon", "night"]
                )
            ]
            return core_items + time_items[:1]  # Add one time-based item

        elif attempt == 2:
            # Core + activity suggestions
            core_items = [item for item in sorted_items if item.priority >= 6]
            activity_items = [
                item
                for item in sorted_items
                if 3 <= item.priority < 6
                and any(
                    word in item.text.lower()
                    for word in ["day", "outside", "get", "lovely", "nice"]
                )
            ]
            return core_items + activity_items[:1]

        elif attempt == 3:
            # Core + multiple lower-priority items
            core_items = [item for item in sorted_items if item.priority >= 6]
            lower_items = [item for item in sorted_items if 2 <= item.priority < 6]
            return core_items + lower_items[:2]  # Add up to 2 lower priority items

        else:  # attempt == 4
            # Use short text variants to fit more content
            self.use_short_format = True
            return sorted_items[:6]  # Try top 6 items with short text

    def _get_actual_line_count(self, narrative_text):
        """Get actual line count using text measurement"""
        try:
            # Try to use TextRenderer for accurate measurement
            if not self._text_renderer:
                self._setup_text_renderer()

            if self._text_renderer:
                # Parse and wrap the text to count actual lines
                segments = self._text_renderer.parse_markup(narrative_text)
                wrapped_lines = self._text_renderer.hard_wrap_text(segments)
                line_count = len(wrapped_lines)
                log(
                    f"Text renderer measured {line_count} lines for text: {narrative_text[:50]}..."
                )
                return line_count

        except Exception as e:
            log(f"Text renderer failed: {e}")

        # Fallback to character estimation
        # 400 chars / 7 lines = ~57 chars per line average
        estimated_lines = max(1, len(narrative_text) // 57)
        result = min(estimated_lines, self.max_lines)
        log(f"Character estimation: {result} lines for {len(narrative_text)} chars")
        return result

    def _fallback_optimize(self, sorted_items):
        """Fallback to original optimization algorithm"""
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
        """Join text parts with smart punctuation handling and Tomorrow: placement"""
        if not parts:
            return ""

        # Extract items by type for better organization
        content_items = []
        for item in parts:
            if hasattr(item, "text"):
                content_items.append(item.text)
            else:
                content_items.append(str(item))

        if not content_items:
            return ""

        if len(content_items) == 1:
            text = content_items[0]
            clean_text = self._strip_formatting_tags(text)
            if clean_text and not clean_text.rstrip().endswith((".", "!", "?")):
                return text + "."
            return text

        # Separate Tomorrow: content from other content
        tomorrow_parts = []
        regular_parts = []

        for part in content_items:
            if "Tomorrow:" in part or "tomorrow" in part.lower():
                tomorrow_parts.append(part)
            else:
                regular_parts.append(part)

        # Join regular parts first
        result = ""
        if regular_parts:
            result = regular_parts[0]
            for part in regular_parts[1:]:
                # Check if previous part already ends with punctuation
                clean_previous = self._strip_formatting_tags(result).rstrip()
                if clean_previous.endswith((".", "!", "?")):
                    result += f" {part}"
                else:
                    result += f". {part}"

        # Add Tomorrow: content with simple space-saving formatting
        if tomorrow_parts:
            result = self._add_tomorrow_simply(result, tomorrow_parts)

        # Ensure final punctuation
        # Ensure final result has appropriate ending punctuation
        if result:
            final_clean = self._strip_formatting_tags(result).rstrip()
            if not final_clean.endswith((".", "!", "?")):
                result += "."

        return result

    def _add_tomorrow_simply(self, current_result, tomorrow_parts):
        """Add Tomorrow: content with simple space-saving - no new lines, just T: vs Tomorrow:"""
        if not tomorrow_parts:
            return current_result

        # Ensure current content ends with punctuation
        if current_result:
            clean_result = self._strip_formatting_tags(current_result).rstrip()
            if not clean_result.endswith((".", "!", "?")):
                current_result += "."

        # Prepare Tomorrow: content
        tomorrow_text = tomorrow_parts[0]
        for i, part in enumerate(tomorrow_parts[1:], 1):
            tomorrow_text += f" {part}"

        # Try "Tomorrow:" first, then "T:" if it doesn't fit
        full_format = f" {tomorrow_text}"
        test_full = current_result + full_format

        if self._get_actual_line_count(test_full) <= self.max_lines:
            log("✓ Tomorrow: using full 'Tomorrow:' format")
            return test_full
        else:
            # Use compact "T:" format
            compact_format = f" {tomorrow_text.replace('Tomorrow:', 'T:', 1)}"
            log("✓ Tomorrow: using compact 'T:' format to save space")
            return current_result + compact_format

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
