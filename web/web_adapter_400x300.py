"""
Web adapter for 400x300 text display
Provides mock data and utilities for web preview
"""

def get_sample_weather_texts():
    """Get sample weather text content for testing"""
    return {
        'current_cold': '''<b>Now:</b> <red>Cloudy</red> conditions with <i>rain</i> expected around <b>2am</b>. Wind gusts up to <b>25mph</b> making it feel like <red>-2°C</red>.

<b>Tomorrow:</b> <red>Sunny</red> and <b>4°C</b> with light winds from the <i>west</i> at 10mph.

<b>Weekend:</b> <bi>Partly cloudy</bi> with temperatures reaching <b>6°C</b>.''',

        'summer_hot': '''<b>Today:</b> <red>Sunny</red> and hot with temperatures reaching <b>32°C</b>. Light winds from the <i>southwest</i> at 8mph.

<b>Tomorrow:</b> <bi>Mostly sunny</bi> with afternoon highs of <b>29°C</b> and overnight lows around <b>18°C</b>.

<b>Weekend:</b> Partly <red>cloudy</red> with a chance of <i>thunderstorms</i> Saturday evening. Temperatures in the <b>mid-20s</b>.''',

        'winter_forecast': '''<b>Current:</b> <red>Snow</red> falling with <b>-8°C</b> and winds from the <i>north</i> at 15mph making it feel like <red>-15°C</red>.

<b>Tonight:</b> Snow continuing with accumulations up to <b>10cm</b> expected. Low <red>-12°C</red>.

<b>Tomorrow:</b> <bi>Clearing skies</bi> with <b>-5°C</b> but still <i>very cold</i> with wind chill.''',

        'spring_mild': '''<b>Now:</b> <red>Partly sunny</b> with comfortable <b>16°C</b> and light <i>variable</i> winds at 5mph.

<b>Today:</b> Perfect weather continues with highs reaching <b>20°C</b> under <bi>mostly sunny</bi> skies.

<b>Weekend:</b> <red>Beautiful</red> spring conditions with temperatures in the <b>low 20s</b> and plenty of sunshine.''',

        'markup_demo': '''This demonstrates the <b>markup system</b> for the 400×300 display.

<b>Bold text</b> stands out for <i>important information</i> like temperatures and conditions.

<red>Red colored text</red> can highlight <red>warnings</red> or <red>severe weather</red> alerts.

<bi>Bold italic text</bi> combines both styles for <bi>maximum emphasis</bi> when needed.

The system handles <b>hard wrapping</b> with <i>hyphenation</i> when words are too long for the display width.''',

        'long_forecast': '''<b>Extended Forecast:</b> A <red>complex weather system</red> is approaching from the west, bringing <i>significant changes</i> to our area over the next several days.

<b>Today:</b> <bi>Partly cloudy</b> becoming <red>overcast</red> this afternoon. High <b>12°C</b>, low <b>4°C</b>. Southwest winds 10-15mph.

<b>Tomorrow:</b> <red>Rain</red> developing in the morning, becoming <i>steady</i> by afternoon. Temperatures falling to <b>8°C</b> by evening.

<b>Weekend:</b> <red>Clearing</red> Saturday with <b>sunny</b> conditions returning. Pleasant <b>15°C</b> both days.'''
    }

def get_text_capacity_info():
    """Get text capacity information for the 400x300 display"""
    # Approximate values based on 20px Vollkorn font
    return {
        'display_width': 400,
        'display_height': 300,
        'estimated_chars_per_line': 35,
        'estimated_lines': 12,
        'total_char_capacity': 420,
        'font_info': 'Vollkorn 20px with variants (regular, bold, italic, bold-italic)'
    }

def validate_markup(text):
    """Validate markup syntax in text"""
    import re

    # Check for unclosed tags
    tags = ['b', 'i', 'bi', 'red']
    errors = []

    for tag in tags:
        open_pattern = f'<{tag}>'
        close_pattern = f'</{tag}>'

        open_count = len(re.findall(open_pattern, text))
        close_count = len(re.findall(close_pattern, text))

        if open_count != close_count:
            errors.append(f"Mismatched {tag} tags: {open_count} opening, {close_count} closing")

    return errors if errors else None

def estimate_display_usage(text):
    """Estimate how much of the display the text will use"""
    import re

    # Remove markup tags for character count
    clean_text = re.sub(r'<[^>]+>', '', text)
    char_count = len(clean_text)

    capacity = get_text_capacity_info()
    usage_percent = min(100, (char_count / capacity['total_char_capacity']) * 100)

    return {
        'character_count': char_count,
        'estimated_usage_percent': round(usage_percent, 1),
        'will_fit': char_count <= capacity['total_char_capacity'],
        'overflow_chars': max(0, char_count - capacity['total_char_capacity'])
    }
