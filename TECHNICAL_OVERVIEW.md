# pinkweather technical overview

## hardware system (300x400/CIRCUITPY)

### core modules
- `code.py` - main loop, wifi management, deep sleep
- `weather_api.py` - provider-agnostic weather data interface
- `openweathermap.py` - api calls and json parsing for openweathermap.org
- `weather_narrative.py` - contextual text generation from weather data
- `forecast_row.py` - hourly forecast display with icons and temperatures
- `header.py` - date, air quality, zodiac, moon phase display
- `text_renderer.py` - markup parsing (bold, italic, red, hyperlegible font)
- `weather_history.py` - sd card persistence for yesterday comparisons

### hardware-specific features
- sd card storage at `/sd/weather_history.json` (10 days retention)
- wifi radio management with clean connect/disconnect cycles
- deep sleep between updates to conserve power
- circuitpython font loading with bitmap fonts
- 400x300 tri-color e-ink display rendering

### data flow
1. wifi connect → openweathermap api calls → timezone conversion to local
2. current weather + 5-day forecast + air quality parsing
3. sunrise/sunset events inserted into forecast timeline
4. yesterday temperature comparison from sd card history
5. weather narrative generation with markup tags
6. display rendering with fonts and icons
7. sd card persistence → deep sleep

### error handling
- dns failure recovery with radio reset
- api timeout handling with retry logic
- missing font fallback to terminal font
- sd card unavailable gracefully handled

## web preview system (web/)

### core modules
- `http_server.py` - development server with real/mock weather switching
- `cached_weather.py` - api caching layer for faster development
- `mock_history.py` - web-specific history management (file + memory)
- `simple_web_render.py` - converts circuitpython display objects to png
- `open_meteo_converter.py` - csv historical data to openweathermap format

### mock data system
- historical csv files with hourly weather data (open-meteo format)
- `generate_scenario_data()` creates openweathermap-compatible json
- timezone handling: csv times parsed as utc, converted to local time
- mock history computed from 10 days of csv data for yesterday comparisons
- monkey-patching of `weather_narrative.compare_with_yesterday` for web

### real api mode
- uses openweathermap api with caching (`web/.cache/`)
- stores real weather history at `web/.cache/weather_history.json`
- same comparison logic as hardware but file-based instead of sd card

### web-specific adaptations
- markup parsing identical to hardware using xml.etree.elementtree
- font metrics simulation for text layout without actual fonts
- display object conversion to pil image for png output
- form controls for scenario selection and timestamp manipulation

### caching strategy
- api responses cached based on url hash
- cache files stored in `web/.cache/` directory
- separate caches for weather data vs historical mock data
- no file writes for mock scenarios (in-memory only)

### timezone considerations
- openweathermap returns utc timestamps
- hardware applies timezone offset during parsing
- mock data: csv utc times → openweathermap parser → local times
- web preview matches hardware timezone handling exactly

## shared components

### weather data format
both systems use identical data structures after provider parsing:
```python
{
    "current": {"current_temp": int, "feels_like": int, ...},
    "forecast": [{"dt": timestamp, "temp": int, "icon": str, ...}],
    "air_quality": {"aqi": int, "description": str},
    "city": {"sunrise": timestamp, "sunset": timestamp}
}
```

### markup system
- `<b>bold</b>` `<i>italic</i>` `<bi>bold-italic</bi>` `<red>red-text</red>`
- `<h>number</h>` for hyperlegible font (temperatures)
- xml parsing handles nested tags and preserves spacing
- hardware renders with bitmap fonts, web simulates with font metrics

### yesterday comparison logic
- shared temperature comparison thresholds in `weather_history.py`
- hardware: sd card storage, web: file storage or mock computation
- identical comparison text generation: "lil' warmer", "much colder", etc.
- red markup styling applied to all comparison text

## development workflow

### hardware testing
1. update `300x400/CIRCUITPY/` files on device
2. monitor serial output for debugging
3. check sd card for persistence testing

### web preview testing
1. `cd web && python http_server.py`
2. toggle "use mock weather data" for historical scenarios
3. adjust timestamp sliders for different time period
4. compare output with hardware behavior

### debugging tools
- extensive logging in both systems
- web preview shows raw narrative with markup tags
- font metrics comparison between hardware and web
- cache inspection via web interface