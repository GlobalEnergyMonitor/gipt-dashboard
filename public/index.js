const converter = new showdown.Converter();
const config = {
    datasets: {}
};
const graphs = {};
const tickers = {
    options: []
};

getData();

async function getData() {
    const urls = ["./assets/page-config.json", "./assets/chart-config.json", "./assets/text-config.json", "./assets/map-bounds_edit.json"];
    const keys = ["dashboard", "charts", "text", "mapBounds"];
    const promises = [];
    for (const url of urls) {
        promises.push(fetch(url));
    }

    Promise.all(promises)
        .then(responses => Promise.all(responses.map(r => r.json())))
        .then(jsonObjects => {
            jsonObjects.forEach((obj, i) => {
                config[keys[i]] = obj;
            })
        })
        .then(() => {
            const dataURLS = [];
            config.dashboard.flourish_ids.forEach(id => {
                dataURLS.push(`./assets/data/${config.charts[id].dataset}.json`);
                config.datasets[id] = [];
            })
            if (config.dashboard.tickers) {
                dataURLS.push('https://public.flourish.studio/visualisation/16565310/visualisation.json') // this assumes we want the same template for all tickers
                dataURLS.push(`./assets/data/${config.dashboard.ticker_data}.json`)
                config.datasets.ticker = {};
            }
            const fetches = [];
            for (const url of dataURLS) {
                fetches.push(fetch(url));
            }
            Promise.all(fetches)
                .then(responses => {
                    return Promise.all(responses.map(r => r.json()))
                })
                .then(jsonObjects => {
                    jsonObjects.forEach((obj, i) => {
                        if (config.dashboard.tickers) {
                            if (i < jsonObjects.length - 2) {
                                config.datasets[config.dashboard.flourish_ids[i]] = obj;
                            } else {
                                if (obj.template && obj.template === '@flourish/number-ticker') config.datasets.ticker.flourish_template = obj;
                                else config.datasets.ticker.data = obj;
                            }
                        } else config.datasets[config.dashboard.flourish_ids[i]] = obj;
                    })
                })
                .then(() => {
                    document.querySelector('h1').innerHTML = markdownToHTML(config.text.title);
                    if (config.dashboard.overall_summary) document.querySelector('.dashboard-intro--para').innerHTML = markdownToHTML(insertOverallSummary());
                    if (config.dashboard.input_type === 'dropdown') implementDropdown();
                    if (config.dashboard.input_type === 'buttons') implementFilterButtons();
                    if (config.text.footer) document.querySelector('.dashboard-footer').innerHTML = markdownToHTML(config.text.footer);
                    // add another to implement combo
                })
                .then(() => renderTickers())
                .then(() => renderVisualisation())
                .then(() => {
                    if (config.dashboard.extra_visualisations) addExtraVisualisations();
                })
                .catch((error) => {
                    console.error(error);
                });
        })
}

function implementDropdown() {
  if (!config.text.dropdown_label) {
    throw new Error('input_label not found or does not match input type. Check page and text configs');
  }

  const label = document.createElement('label');
  label.innerHTML = markdownToHTML(config.text.dropdown_label);
  label.for = "dropdown-selection";

  const dropdownEl = document.createElement('select');
  dropdownEl.id = "dropdown-selection";

  if (!config.text.dropdown) {
    throw new Error('page-config specifies input of dropdown but text-config does not match');
  }

  let dropdownData = (typeof config.dashboard.input_filter === 'string')
    ? config.text.dropdown.map(entry => entry[config.dashboard.input_filter])
    : config.dashboard.input_filter;

  dropdownData.forEach(input => {
    const opt = document.createElement('option');
    opt.value = formatName(input); // formatted for uniqueness
    opt.text = input;              // display string from dataset
    dropdownEl.appendChild(opt);
  });

  const controlsContainer = document.querySelector('.controls-container');
  controlsContainer.appendChild(label);
  controlsContainer.appendChild(dropdownEl);
  controlsContainer.classList.add('controls-container--dropdown');

  const onSelect = (evt) => {
    // ✅ Use the visible label directly instead of trying to reverse map
    const selectedDisplay = evt.target.options[evt.target.selectedIndex].text;
    updateSummaries(selectedDisplay);
    updateGraphs(selectedDisplay);
  };

  dropdownEl.addEventListener('change', onSelect, { passive: true });
}

function implementFilterButtons() {
    if (!config.text.buttons_label) throw new Error('input_label not found or does not match input type. Check page and text configs')
    const label = document.createElement('legend');
    label.innerHTML = markdownToHTML(config.text.buttons_label);
    label.for = "button-group"
    const btnGroup = document.createElement('fieldset');
    btnGroup.classList.add('button-group');
    btnGroup.appendChild(label);

    btnsWrapper = document.createElement('div');
    btnsWrapper.classList.add('buttons-wrapper');
    btnGroup.appendChild(btnsWrapper);

    if (!config.text.buttons) throw new Error('page-config specifies input of buttons but text-config does not match')

    let buttonData = (typeof config.dashboard.input_filter === 'string') ?
        config.text.buttons.map(entry => entry[config.dashboard.input_filter]) :
        config.dashboard.input_filter;

    buttonData.forEach((button, i) => {
        const btnContainer = document.createElement('div');
        btnContainer.classList.add('filter-button');

        const btn = document.createElement('input');
        btn.type = 'radio';
        if (i === 0) btn.checked = "checked";
        // btn.classList.add('filter-button');
        btn.value = formatName(button);
        btn.id = formatName(button);
        btn.text = button;
        btn.name = 'filter';
        const label = document.createElement('label');
        label.innerHTML = button;
        label.for = formatName(button);

        btnContainer.appendChild(label);
        btnContainer.appendChild(btn);
        btnsWrapper.appendChild(btnContainer);
    });
    const controlsContainer = document.querySelector('.controls-container');
    controlsContainer.appendChild(btnGroup);
    controlsContainer.classList.add('controls-container--buttons');

    const buttonEls = document.querySelectorAll('.filter-button input');
    buttonEls.forEach(btn => {
        btn.addEventListener('click', (evt) => {
            buttonEls.forEach(btnEl => btnEl.checked = false);
            evt.target.checked = "checked";

            const selectedValue = evt.target.value;
            updateSummaries(selectedValue);
            updateGraphs(selectedValue);
        })
    });
}

function renderTickers() {
    if (config.dashboard.tickers) {
        const container = document.createElement('div');
        container.classList.add('tickers-container');
        document.querySelector('.dashboard-intro').appendChild(container);
        const initialData = initialTickerData()[0];

        const {
            state
        } = config.datasets.ticker.flourish_template;
        if (config.dashboard["ticker_text_font-size"]) {
            const tickerTextSplit = config.dashboard["ticker_text_font-size"]
                .match(/[a-zA-Z]+|[0-9]+(?:\.[0-9]+)?|\.[0-9]+/g); // grab text size from config and split into size and unit needed in flourish:
            state.font_size = tickerTextSplit[0];
            state.font_unit = tickerTextSplit[1]
        }

        const options = {
            template: "@flourish/number-ticker",
            version: '1.5.1',
            api_url: "/flourish",
            api_key: "", //filled in server side
            state: {
                ...state
            }
        };

        config.dashboard.tickers.forEach((entry, i) => {
            const {
                id
            } = entry;
            const container = document.createElement('div');
            container.id = id;
            container.classList.add('ticker-container');
            document.querySelector('.tickers-container').appendChild(container);

            const tickerConf = config.dashboard.tickers.filter(entry => entry.id === id)[0];
            tickers[id] = {};
            tickers[id].options = {
                ...options,
                container: `#${id}`,
                state: {
                    ...options.state,
                    custom_template: formatWithTickerStyling(initialData, id),
                    value_format: {
                        ...options.state.value_format,
                        n_dec: tickerConf.decimal_places,
                    }
                }
            }
            tickers[id].flourish = new Flourish.Live(tickers[id].options);
            tickers[id].flourish.iframe.style.width = "100%"; // needed to override full width in safari
        });
    }
}

function updateTickers() {
    config.dashboard.tickers.forEach((entry, i) => {
        const {
            id
        } = entry;
        const data = filterTickerData(getSelectedText());
        if (data[id]) {
            tickers[id].options.state.custom_template = formatWithTickerStyling(data, id)
            tickers[id].flourish.update(tickers[id].options)
            document.querySelector(`#${id} iframe`).style.opacity = 1;
        } else document.querySelector(`#${id} iframe`).style.opacity = 0.3;
    });
}

function formatWithTickerStyling(data, id) {
    const text = data[id];
    const {
        style
    } = config.dashboard.tickers.filter(entry => entry.id === id)[0];
    const colourOverride = data[`${id}_color`];
    const styledSpan = Object.entries(style).reduce((prev, [key, val]) => `${prev} ${key}: ${(key === 'color' && colourOverride) ? colourOverride : val};`, '<span style="') + '">';
    return text.replace('<span>', styledSpan);
}

function insertOverallSummary() {
    let summaryObj = config.text[(config.dashboard.input_type === 'dropdown') ? 'dropdown' : 'buttons'];
    const filterKey = (typeof config.dashboard.input_filter === 'string') ? config.dashboard.input_filter : config.dashboard.input_key;
    summaryObj = summaryObj.filter(entry => entry[filterKey] === config.dashboard.input_default)[0];
    if (!summaryObj.overall_summary) throw new Error('Overall Summary set to true but no text values given');
    return summaryObj.overall_summary;
}

function insertChartSummary(id) {
    const currentGraph = config.charts[id];
    if (currentGraph.summary) {
        const summary = document.createElement('p');
        summary.classList.add('chart-summary');
        let summaryTextObj;

        if (typeof currentGraph.filter_by === 'string') {
            summaryTextObj = filterSummaries(currentGraph.filter_by, config.charts[id].initial_state);
        } else {
            summaryTextObj = config.text[(config.dashboard.input_type === 'dropdown') ? 'dropdown' : 'buttons'].filter(entry => entry[config.dashboard.input_key] === config.dashboard.input_default)[0];
        }
        if (summaryTextObj[currentGraph.summary]) {
            summary.innerHTML = markdownToHTML(summaryTextObj[currentGraph.summary]);
            document.querySelector(`#chart-${id}`).appendChild(summary);
        }
    }
}

function updateSummaries(selectedDisplay) {
  const filterKey = (typeof config.dashboard.input_filter === 'string')
    ? config.dashboard.input_filter
    : config.dashboard.input_key;

  const summaryTextObj = filterSummaries(filterKey, selectedDisplay);

  if (config.dashboard.overall_summary) updateOverallSummary(summaryTextObj);
  if (config.dashboard.tickers) updateTickers(selectedDisplay);
  updateGraphSummaries(selectedDisplay, summaryTextObj);
}
function filterSummaries(key, selected) {
    const summaryObj = config.text[(config.dashboard.input_type === 'dropdown') ? 'dropdown' : 'buttons'];
    return summaryObj.filter(entry => entry[key] === selected)[0];
}

function updateOverallSummary(summaryTextObj) {
    document.querySelector('.dashboard-intro--para').innerHTML =
        markdownToHTML((summaryTextObj.overall_summary) ? summaryTextObj.overall_summary : '');
}

function updateGraphSummaries(selectedDisplay, summaryTextObj) {
  const graphIDs = config.dashboard.flourish_ids;
  graphIDs.forEach(id => {
    const currentGraph = config.charts[id];
    if (currentGraph.filterable && currentGraph.summary) {
      let filteredData;
      if (typeof currentGraph.filter_by === 'string') {
        filteredData = config.datasets[id].filter(entry =>
  formatName(entry[currentGraph.filter_by]) === formatName(selectedDisplay)
);
      } else {
        filteredData = (selectedDisplay === 'All')
          ? config.datasets[id]
          : filterDataOnColumnName(selectedDisplay, id);
      }
      const summary = document.querySelector(`#chart-${id} .chart-summary`);
      if (summary) {
        summary.innerHTML = markdownToHTML(
          (filteredData.length <= 0 || !summaryTextObj[currentGraph.summary])
            ? config.text.no_data.replace("{{selected}}", selectedDisplay)
            : summaryTextObj[currentGraph.summary]
        );
      }
    }
  });
}

function renderVisualisation() {
  const graphIDs = config.dashboard.flourish_ids;

  graphIDs.forEach(id => {
    if (document.querySelector(`#chart-${id}`)) return; // 🔑 prevent duplicates

    const container = document.createElement('div');
    container.id = `chart-${id}`;
    container.classList.add('chart-container');

    if (String(id) === "24167887") {
      container.classList.add('map-chart-container');
    }

    document.querySelector('.flourish-container').appendChild(container);

    insertChartSummary(id);
    implentGraph(id);
  });
}

function renderMap(id, selected) {
  const fullData = config.datasets[id];
  const sel = selected.trim().toLowerCase();

  let filtered;

  if (sel === "world" || sel === "g20") {
    // ✅ World & G20 case: only keep plants above 50 MW
    filtered = fullData.filter(entry => {
      const cap = Number(entry["Capacity (MW)"]);
      return !isNaN(cap) && cap >= 50;
    });
  } else {
    // ✅ Country/region case: existing filter
    filtered = fullData.filter(entry => {
      const country = entry["Country/area"]?.trim().toLowerCase();
      const regions = Array.isArray(entry["Region"])
        ? entry["Region"].map(r => r.trim().toLowerCase())
        : [];
      return country === sel || regions.includes(sel);
    });
  }

  const headers = [
    "Plant / Project name","Capacity (MW)","Technology","Country/area",
    "Latitude","Longitude","Type","Capacity (MW)","Type"
  ];

  const mapped = filtered.map(entry => [
    entry["Plant / Project name"],
    entry["Capacity (MW)"],
    entry["Technology"],
    entry["Country/area"],
    entry["Latitude"],
    entry["Longitude"],
    entry["Type"],
    entry["Capacity (MW)"],
    entry["Type"]
  ]);

  const bounds = config.mapBounds[selected] || config.mapBounds["World"];
  const containerId = `chart-${id}`;
  const container = document.querySelector(`#${containerId}`);

  // Reset Flourish iframe
  const oldIframe = container.querySelector("iframe");
  if (oldIframe) oldIframe.remove();

  graphs[id] = graphs[id] || {};
  graphs[id].flourish = new Flourish.Live({
    template: "@flourish/time-map",
    version: "17.5.2",
    bindings: {
      events: { metadata:[0,1,2,3], lat:4, lon:5, name:6, scale:7, color:8 },
      lines: { geojson:0, series:1 },
      regions: { geojson:0 },
      regions_map: { geojson:0, metadata:[], name:1, value:[2] }
    },
    container: `#${containerId}`,
    api_url: "/flourish",
    api_key: "ZkqdL7nzFCQAihbjv-7j0UIm_r3rCCq-IYy4JfCahp9Qs-_dmIGzLn4O_DpcEhiv",
    base_visualisation_id: id,
    data: { events: [headers, ...mapped] },
    state: {
      ...config.charts[id]?.state,
      map: {
        ...(config.charts[id]?.state?.map || {}),
        map_initial_bounds_lat_min: bounds.lat_min,
        map_initial_bounds_lat_max: bounds.lat_max,
        map_initial_bounds_lng_min: bounds.lng_min,
        map_initial_bounds_lng_max: bounds.lng_max,
        map_initial_type: "bounding_box"
      }
    }
  });
}


function implentGraph(id) {
  graphs[id] = {};

  // Special case for the time-map chart
  if (id === "24167887") {
  const selected = getSelectedText();
  renderMap(id, selected);
  return;
}

    // Scatter
    fetch(`https://public.flourish.studio/visualisation/${id}/visualisation.json`)
        .then((response) => response.json())
        .then((options) => {
            const data = config.datasets[id];
            // 
            if (options.template === "@flourish/scatter" || (config.charts[id] && config.charts[id].type === "scatter")) {
                const currentGraph = config.charts[id];

                const filteredData = initialData(id);

                // EXACT headers the vis was authored with (duplicates are intentional)
                const headers = [
                    "Age Category", "Type", "Country", "Type", "Country", "Type", "Age Category", "Capacity (GW)", "Capacity %", "Capacity %"
                ];

                const rows = filteredData.map(d => {
                    // Optional fallback: derive GW if only MW exists
                    const capGW =
                        d["Capacity (GW)"] != null ? d["Capacity (GW)"]
                            : (d["Capacity (MW)"] != null ? Number(d["Capacity (MW)"]) / 1000 : null);

                    return [
                        d["Age Category"],         // 0  x
                        d["Type"],                 // 1  color
                        d["Country"],              // 2  filter
                        d["Type"],                 // 3  y
                        d["Country"],              // 4  metadata[0]
                        d["Type"],                 // 5  metadata[1]
                        d["Age Category"],         // 6  metadata[2]
                        capGW,                     // 7  metadata[3]
                        d["Capacity %"],           // 8  metadata[4]
                        d["Capacity %"]            // 9  size
                    ];
                });

                graphs[id].opts = {
                    template: "@flourish/scatter",
                    version: "33.4.2",
                    container: `#chart-${id}`,
                    api_url: "/flourish",
                    api_key: "",
                    base_visualisation_id: id,
                    // Use index-based bindings to match the authored vis exactly
bindings: {
  data: {
    name: [],
    x: 0,
    color: 1,
    y: 3,
    metadata: [4, 5, 6, 7, 8],
    size: 9
  }
},
                    data: { data: [headers, ...rows] },
                    // Keep state minimal to avoid referencing missing columns
                    state: {
                        layout: {
                            title: (currentGraph.title || '').replace('{{country}}', ''),
                            subtitle: currentGraph.subtitle || ''
                        }
                    }
                };

                graphs[id].flourish = new Flourish.Live(graphs[id].opts);
                graphs[id].ready = true;
                return;
            }

            const hierarchyCharts = {
                "23191160": {
                    filter: "Country",
                    nest_columns: ["Type", "Parent"],
                    size_columns: ["Capacity (GW)"]
                },
                "23185423": {
                    filter: "Country",
                    nest_columns: ["Type", "Starts", "Status"],
                    size_columns: ["Capacity (GW)"]
                }
            };

            if (hierarchyCharts[id]) {
                const bindings = hierarchyCharts[id];

                graphs[id].opts = {
                    ...options,
                    container: `#chart-${id}`,
                    api_url: "/flourish",
                    api_key: "",
                    base_visualisation_id: id,
                    bindings: {
                        data: bindings
                    },
                    data: {
                        data: data
                    }
                };

                graphs[id].flourish = new Flourish.Live(graphs[id].opts);
                return;
            }

            // Standard charts
            graphs[id].opts = {
                ...options,
                container: `#chart-${id}`,
                api_url: "/flourish",
                api_key: "ZkqdL7nzFCQAihbjv-7j0UIm_r3rCCq-IYy4JfCahp9Qs-_dmIGzLn4O_DpcEhiv",
                base_visualisation_id: id,
                bindings: {
                    ...options.bindings,
                    data: {
                        ...options.bindings.data,
                        label: config.charts[id].x_axis,
                        value: config.charts[id].values
                    }
                },
                data: {
                    ...options.data,
                    data: initialData(id),
                },
                state: {
                    ...options.state,
                    layout: {
                        title: (config.charts[id].title || '').replace('{{country}}', ''),
                        subtitle: config.charts[id].subtitle || ''
                    }
                }
            };

            if (options.template === "@flourish/line-bar-pie") {
                graphs[id].opts.version = 25;
            }

            graphs[id].flourish = new Flourish.Live(graphs[id].opts);
        });
}

function updateGraphs(selectedDisplay) {
  const graphIDs = config.dashboard.flourish_ids;

  graphIDs.forEach(id => {
    const currentGraph = config.charts[id];

    // --- Map special case ---
    if (id === "24167887") {
      renderMap(id, selectedDisplay);
      return;
    }

    // --- Shared filtering ---
    let filteredData = config.datasets[id];
    if (currentGraph.filterable) {
      if (typeof currentGraph.filter_by === 'string') {
        filteredData = config.datasets[id].filter(entry =>
          formatName(entry[currentGraph.filter_by]) === formatName(selectedDisplay)
        );
      } else {
        filteredData = (selectedDisplay === 'All')
          ? config.datasets[id]
          : filterDataOnColumnName(selectedDisplay, id);
      }
    }

// --- Scatter ---
const isScatter =
  graphs[id]?.opts?.template === "@flourish/scatter" ||
  currentGraph?.type === "scatter";

if (isScatter) {
  const headers = [
    "Age Category","Type","Country","Type","Country","Type",
    "Age Category","Capacity (GW)","Capacity %","Capacity %"
  ];

  const rows = filteredData.map(d => {
    const mw = d["Capacity (MW)"];
    const gwFromMW = (mw == null || mw === "") ? null : Number(String(mw).replace(/[, ]+/g, "")) / 1000;
    const gw = d["Capacity (GW)"] != null ? Number(d["Capacity (GW)"]) : gwFromMW;
    const pct = d["Capacity %"] != null ? Number(d["Capacity %"]) : null;
    return [
      d["Age Category"], d["Type"], d["Country"], d["Type"], d["Country"],
      d["Type"], d["Age Category"], gw, pct, pct
    ];
  });

  if (graphs[id]?.flourish) {
    // 1) Update data only
    graphs[id].flourish.update({
      template: "@flourish/scatter",
      bindings: { data: { name: [], x:0, color:1, filter:2, y:3, metadata:[4,5,6,7,8], size:9 } },
      data: { data: [headers, ...rows] },
      animate: false
    });

    // 2) Update layout in next frame
    requestAnimationFrame(() => {
      graphs[id].flourish.update({
        state: {
          layout: {
            title: (currentGraph.title || '').replace('{{country}}', selectedDisplay),
            subtitle: currentGraph.subtitle || ''
          }
        },
        animate: false
      });
    });

    const iframe = document.querySelector(`#chart-${id} iframe`);
    if (iframe) iframe.style.opacity = rows.length ? 1 : 0.3;
  }

  return;
}

    // --- Hierarchy ---
    const isHierarchy =
      graphs[id]?.opts?.template === "@flourish/hierarchy" ||
      ["23191160", "23185423"].includes(id);

    if (isHierarchy) {
      graphs[id].flourish.update({
        template: graphs[id].opts.template,
        bindings: graphs[id].opts.bindings,
        data: { data: filteredData },
        animate: true
      });
      return;
    }

    // --- Default ---
    if (filteredData.length !== 0) {
      graphs[id].flourish.update({
        template: graphs[id].opts.template,
        version: graphs[id].opts.version,
        container: graphs[id].opts.container,
        api_url: graphs[id].opts.api_url,
        api_key: graphs[id].opts.api_key,
        base_visualisation_id: id,
        bindings: graphs[id].opts.bindings,
        state: graphs[id].opts.state,
        data: { data: filteredData },
        animate: true
      });
      const iframe = document.querySelector(`#chart-${id} iframe`);
      if (iframe) iframe.style.opacity = 1;
    } else {
      const iframe = document.querySelector(`#chart-${id} iframe`);
      if (iframe) iframe.style.opacity = 0.3;
    }
  });
}

function formatName(string) {
    return string.toLowerCase().replace(/ /g, "_");
}

function getUnformattedInputName(string) {
    if (Array.isArray(config.dashboard.input_filter)) {
        for (const key of config.dashboard.input_filter) {
            if (formatName(key) === string) return key;
        }
    } else {
        // input_filter is a string — use it to search actual dropdown values
        const dropdownData = config.text.dropdown || [];
        for (const entry of dropdownData) {
            const candidate = entry[config.dashboard.input_filter];
            if (formatName(candidate) === string) return candidate;
        }
    }
    return string; // fallback: return original
}

function initialData(id) {
    let data = config.datasets[id];
    if (config.charts[id].filterable) {
        if (typeof config.charts[id].filter_by === 'string') {
    const by = config.charts[id].filter_by;
    const target = formatName(config.charts[id].initial_state);
    data = config.datasets[id].filter(entry => formatName(entry[by]) === target);
} else {
            const defaultFilter = config.dashboard.input_default;
            if (defaultFilter === "All") return data;
            else return filterDataOnColumnName(formatName(defaultFilter), id)
        }
    }
    return data;
}

function filterDataOnColumnName(selectedDisplay, id) {
  const x_value = config.charts[id].x_axis;
  const filteredData = config.datasets[id].map(entry => {
    const output = {};
    output[selectedDisplay] = entry[selectedDisplay];
    output[x_value] = entry[x_value];
    return output;
  });
  return filteredData;
}
function initialTickerData() {
    return config.datasets.ticker.data.filter(entry => entry[config.dashboard.input_filter] === config.dashboard.input_default);
}

function filterTickerData(key) {
    return config.datasets.ticker.data.filter(entry => entry[config.dashboard.input_filter] === key)[0];
}

function getSelectedText() {
    if (config.dashboard.input_type === 'dropdown') {
        const dropdown = document.querySelector('select');
        return dropdown[dropdown.selectedIndex].text;
    } else if (config.dashboard.input_type === 'buttons') {
        const selectedButton = document.querySelector('input[name="filter"]:checked');
        return selectedButton.text;
    }
}

function getSelectedButton() {
    const dropdown = document.querySelector('select');
    return dropdown[dropdown.selectedIndex].text;
}

function markdownToHTML(string) {
    return converter.makeHtml(string).replace(/<\/?p[^>]*>/g, '');;
}

function addExtraVisualisations() {
    const wrapper = document.createElement('div');
    wrapper.classList.add('vis-container');
    document.querySelector('body').insertBefore(wrapper, document.querySelector('.dashboard-footer'))
    const IDsToAdd = config.dashboard.extra_visualisations;
    IDsToAdd.forEach(id => {
        const container = document.createElement('div');
        container.id = `vis-${id}`;
        container.classList.add('chart-container');
        wrapper.appendChild(container);
        new Flourish.Live({
            container: `#vis-${id}`,
            api_url: "/flourish",
            api_key: "",
            base_visualisation_id: id,
        });
    });
}

