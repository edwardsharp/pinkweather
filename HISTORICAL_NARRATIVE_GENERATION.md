# historical narrative generation plan

## overview

generate comprehensive dataset of weather narratives using historical csv data for testing and refinement. create static html viewer for keyboard navigation through historical weather displays without requiring python server.

## data generation pipeline

### 1. csv narrative dataset
```python
# target csv format
timestamp,date,hour,narrative_text,text_length_px,text_height_px,line_count,fits_display,temp,weather_desc
1704067200,2024-01-01,00:00,"clear and cold, 2°...",245,68,3,true,2,clear
```

### 2. image generation
- generate png files for each hour: `2024-01-01-00-00.png`
- use existing `simple_web_render.py` pipeline
- capture actual rendered dimensions from pil
- store images in `static/images/` directory
- add new .py and related code in `static/` directory

### 3. batch processing script
```python
# pseudo-code structure
def generate_historical_dataset():
    csv_data = load_historical_csv()
    results = []
    
    for hour_data in csv_data:
        # generate weather data structure
        weather_data = convert_to_weather_format(hour_data)
        
        # generate narrative
        narrative = generate_narrative(weather_data)
        
        # render to image and measure
        image, metrics = render_and_measure(weather_data, narrative)
        
        # save image file
        save_image(image, hour_data.timestamp)
        
        # collect metrics
        results.append({
            'timestamp': hour_data.timestamp,
            'narrative': narrative,
            'metrics': metrics
        })
    
    save_csv(results)
```

## text measurement system

### pil-based metrics
- use same font loading as `simple_web_render.py`
- measure actual text bounding boxes
- account for line wrapping at display width (400px)
- detect text overflow beyond display height (300px)

### measurement functions
```python
def measure_narrative_text(narrative, fonts):
    # parse markup and measure each styled segment
    # calculate line breaks based on display width
    # return pixel dimensions and overflow status
    
def fits_display(text_metrics, display_bounds=(400, 300)):
    # return boolean if text fits within display constraints
```

### collected metrics
- total text width/height in pixels
- number of lines after wrapping
- overflow status (fits/overflow)
- character count (for comparison)
- markup complexity (tag count)

## static html viewer

### file structure
```
static/
├── narratives.csv           # complete dataset
├── images/                  # hourly png files
│   ├── 2024-01-01-00-00.png
│   ├── 2024-01-01-01-00.png
│   └── ...
└── viewer.html              # standalone viewer
```

### html viewer features
- a very minimal html page, dark theme (use pure black, pure white, and magenta for accent color).
- keyboard navigation (arrow keys, page up/down)
- display current image with metadata overlay
- show narrative text and metrics (can toggle displaying this, default off (hidden))
- jump to specific dates/times (simple html select form)
- filter by overflow status (start with just one html select form here with a list of dates that have overflow)
- progress indicator (current timestamp hour X of Y)

### viewer implementation
```html
<!-- embedded javascript loads narratives.csv -->
<!-- preloads image files for smooth navigation -->
<!-- keyboard event handlers for navigation -->
<!-- responsive layout for different screen sizes -->
```

## generation workflow

### phase 1: data extraction
1. load historical csv files (open-meteo format)
2. convert hourly data to weather api format
3. generate weather narratives for each hour
4. measure text dimensions using pil
5. save results to csv dataset

### phase 2: image generation
1. render each hour using `simple_web_render.py`
2. save png files with timestamp naming
3. optimize file sizes for web loading
4. generate thumbnail images (optional)

### phase 3: viewer creation
1. create standalone html file
2. embed csv data as javascript
3. implement keyboard navigation
4. add filtering and search capabilities
5. include metadata display overlay

## narrative refinement process

### testing methodology
1. generate baseline dataset with current narrative code
2. identify common overflow cases from csv metrics
3. modify narrative generation logic
4. regenerate dataset and compare metrics
5. iterate until overflow rate is minimized

### optimization targets
- minimize text overflow while maintaining readability
- balance information density with space constraints
- test edge cases (extreme weather, long place names)
- ensure consistent formatting across scenarios

## implementation considerations

### performance
- batch processing with progress indicators
- parallel image generation for speed
- compressed image formats for storage
- lazy loading in html viewer

### extensibility
- configurable display dimensions for testing
- support for different font combinations
- plugin system for narrative variations
- export formats (json, sqlite)

### validation
- cross-check generated data with hardware output
- verify font metrics match actual device
- test viewer compatibility across browsers
- validate csv data integrity

## file organization

```
scripts/
├── generate_historical_data.py  # main generation script
├── narrative_measurement.py     # text metrics functions
├── batch_image_renderer.py      # png generation
└── html_viewer_generator.py     # static site builder
```

## success metrics

- complete hourly coverage for 1+ years of data
- text overflow rate < 5% of generated narratives
- viewer loads and navigates smoothly
- generated images match hardware output visually
- csv dataset enables rapid iteration on narrative code
