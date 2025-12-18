# TfL Analytics Dashboard 🚇🗺️

A real-time analytics dashboard for Transport for London (TfL) services. This web application provides live service status, disruption summaries, bus route issues, station-level impact visualisation, and an interactive journey planner. All powered by live TfL data.

---

## Live Demo




---

## Features

###  Real-Time Line Status
- Live status for all Tube lines
- Clear indicators for **Good Service**, **Minor Delays**, **Severe Delays**, and closures
- Disruption alerts for selected lines

###  Bus Disruptions
- Full table of current bus route disruptions
- Search for specific bus routes
- Status highlighting for quick scanning

### Network Summary KPIs
- Total number of Tube stations
- Stations affected by disruptions
- Number of disrupted lines
- Percentage of the network impacted

### Interactive Station Map
- Map of **Tube stations only**
- Stations colour-coded by worst service status
- Clustered markers for performance
- Clickable popups showing line-level status per station

### Filters & Alerts
- Filter by specific lines
- Filter by disruption severity
- Automatic disruption alerts for selected criteria

### Journey Planner
- Dropdown-based station selection
- Multiple journey options with:
  - Total duration
  - Number of changes
  - Step-by-step journey legs
  - Transport mode breakdown (Tube, Bus, DLR, Walking)

---

## Technologies Used

- **Frontend / App Framework:** Streamlit  
- **Data Processing:** Python, Pandas, NumPy  
- **Mapping:** Folium, streamlit-folium  
- **Visualisation:** Streamlit charts, Folium maps  
- **Caching & Performance:** Streamlit caching  

---
## Local Development (Optional)

If you want to run the project locally:

```bash
git clone https://github.com/kartalceren1/tfl-analytics-dashboard.git
cd tfl-analytics-dashboard
python -m venv venv
source venv/bin/activate
streamlit run dashboard.py
```


