# historical narrative generation plan - revised approach

## problem assessment

we have TWO systems that should share the same core logic but currently don't:

1. **web server preview** - WORKS PERFECTLY: loads CSV, generates history, creates narratives with "much warmer than yesterday", renders images with proper air quality/zodiac
2. **static dataset generation** - BROKEN: duplicated logic, missing features, complex fallbacks

## core insight

the web server can already render ONE perfect image from historical CSV data. we need to extract that working logic and reuse it for batch processing, not recreate it.

## current working flow (from web server)

```
http_server.py receives request with timestamp
  ↓
mock_weather_data.py generates weather data from CSV  
  ↓
mock_history.py computes 10 days of history from CSV
  ↓ 
weather_narrative.py generates narrative WITH history comparisons
  ↓
simple_web_render.py renders final image
```

this WORKS and has:
- real CSV weather data (no fallbacks)
- proper weather history ("much warmer than yesterday")  
- correct air quality (AQI: 2, Fair)
- correct zodiac signs
- proper sunrise/sunset times
- tomorrow forecasts in narratives

## refactoring plan

### phase 1: extract core logic

create shared module that both web server AND static scripts can use:

```python
# web/shared_weather_engine.py

def generate_weather_display_for_timestamp(csv_path, timestamp):
    """
    Core function that both web server and static scripts call
    Returns: (weather_data, narrative, display_vars, current_weather)
    """
    # use existing mock_weather_data.py logic
    # use existing mock_history.py logic  
    # use existing weather_narrative.py logic
    # return structured data for rendering

def render_weather_to_image(weather_data, narrative, display_vars, current_weather):
    """
    Core rendering function 
    Returns: PIL image
    """
    # use existing simple_web_render.py logic
```

### phase 2: refactor web server

```python
# http_server.py (simplified)

@POST /preview 
def handle_preview():
    timestamp = request.form['mock_timestamp']
    weather_data, narrative, display_vars, current_weather = generate_weather_display_for_timestamp(CSV_PATH, timestamp)
    image = render_weather_to_image(weather_data, narrative, display_vars, current_weather)
    return image
```

### phase 3: refactor static scripts

```python  
# static/generate_historical_data.py (simplified)

def generate_dataset(csv_path, max_records=None):
    csv_records = load_csv_timestamps(csv_path)
    
    for timestamp in csv_records[:max_records]:
        # REUSE the working web server logic
        weather_data, narrative, display_vars, current_weather = generate_weather_display_for_timestamp(csv_path, timestamp)
        
        # measure text dimensions
        metrics = measure_narrative_text(narrative)
        
        # save to results CSV
        save_result(timestamp, narrative, metrics, weather_data)
        
        # generate image 
        image = render_weather_to_image(weather_data, narrative, display_vars, current_weather)
        save_image(image, timestamp)
```

## key principles

1. **ONE SOURCE OF TRUTH**: core logic lives in shared module, not duplicated
2. **REUSE EXISTING WORKING CODE**: extract from web server, don't recreate
3. **MINIMAL CHANGES**: web server should barely change, just call shared functions
4. **NO FALLBACKS**: use real CSV data only, no +3/-3 calculations
5. **SEPARATION OF CONCERNS**: 
   - shared module: weather data generation
   - web server: HTTP handling
   - static scripts: batch processing and file I/O

## implementation steps

### step 1: create web/shared_weather_engine.py
- extract core logic from http_server.py POST handler
- extract mock weather generation from mock_weather_data.py
- extract history computation from mock_history.py
- create clean interface functions

### step 2: refactor web server to use shared engine
- modify http_server.py to call shared functions
- test that web preview still works identically
- ensure no regressions in functionality

### step 3: refactor static scripts to use shared engine  
- replace weather_data_converter.py with calls to shared engine
- simplify generate_historical_data.py dramatically
- remove all duplicated logic and fallback calculations

### step 4: test and validate
- verify static generation produces same images as web server
- confirm weather history comparisons work in static generation
- ensure air quality, zodiac, sunrise/sunset times are correct

## expected outcomes

- static scripts become much simpler (call shared functions vs complex logic)
- web server barely changes (just calls shared functions)
- identical output between web preview and static generation
- single place to fix bugs or add features
- no more duplicate logic hell

## implementation considerations

### error handling
- fail fast approach - throw errors and stop on missing/corrupt data
- no graceful degradation or partial dataset generation
- validate CSV structure upfront and abort if fields missing

### testing strategy  
- test by running web server after changes to ensure still works
- don't over-engineer - be reasonable and smart about modifications
- modify in place rather than building parallel systems

### performance
- don't worry about performance optimization for this tool
- it's for generating test samples, not production use
- worry about caching/optimization later if needed

### backwards compatibility
- no backwards compatibility concerns
- this isn't rocket science, don't over-engineer

### default values
- minimize fallbacks where possible, use real CSV data
- only use defaults when absolutely necessary (like air quality: aqi=1, "Good")
- avoid adding more UI defaults - want to test against more variable data

## cleanup plan for existing static/ files

### files to KEEP (simplified):
- `generate_historical_data.py` - rewritten to call shared engine
- `batch_image_renderer.py` - rewritten to call shared engine  
- `narrative_measurement.py` - unchanged (text measuring logic)
- `inject_data.py` - unchanged (HTML template injection)
- `template.html` - unchanged
- `narratives.csv` - generated output file
- `viewer.html` - generated output file
- `images/` - generated output directory

### files to DELETE (legacy code):
- `weather_data_converter.py` - ENTIRE FILE DELETED (replaced by shared engine)
- `__pycache__/` - deleted

### no dead code policy:
- any function/class not used after refactoring gets deleted immediately
- no commented out code left behind
- no "TODO: remove this" comments

## file structure after refactoring

```
web/
├── shared_weather_engine.py     # NEW: extracted core logic  
├── http_server.py               # simplified: calls shared functions
├── mock_weather_data.py         # maybe absorbed into shared engine
├── mock_history.py              # maybe absorbed into shared engine
├── weather_narrative.py         # unchanged
└── simple_web_render.py         # unchanged

web/static/
├── generate_historical_data.py  # rewritten: calls shared engine
├── batch_image_renderer.py      # rewritten: calls shared engine  
├── narrative_measurement.py     # unchanged
├── inject_data.py              # unchanged
├── template.html               # unchanged
├── narratives.csv              # generated output
├── viewer.html                 # generated output
└── images/                     # generated output directory
```

## success criteria

- web preview continues to work exactly as before
- static generation produces identical images to web preview for same timestamp
- weather history comparisons appear in static generated narratives
- air quality shows "AQ: FAIR, AQI: 2" not "AQ: UNKNOWN"
- zodiac signs appear correctly
- sunrise/sunset times are realistic, not 6:00/18:00
- codebase has 90% less duplication
- adding new features requires changes in only one place