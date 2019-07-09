# floweaver-path example

![Demo](https://github.com/fullflu/floweaver-path/demo/floweaver_path_demo.gif)

I implement [floweaver-path](https://github.com/fullflu/floweaver-path), an extension of the [floweaver](https://sankeyview.readthedocs.io/en/latest/) to handle the visualization of paths that pass through a selected node.

It would be reasonable to maintain floweaver-path apart from the original floweaver at the moment.
Therefore, I describe only the summary of the extension and put the minimum resources (`data/template.csv` and `template_before_separation.ipynb`) here.

Please check my repository above if you want to know the details of how floweaver-path works.

If you have any questions, please feel free to ask me ([@fullflu](https://github.com/fullflu)).

## Summary
We focus on the visualization of longitudinal data.

The idea of our visualization is based on [pathSankey](https://bl.ocks.org/jeinarsson/e37aa55c3b0e11ae6fa1), that is an extension of [d3-sankey](https://github.com/d3/d3-sankey).

The color of paths that pass through a selected node is yellow-green (highlighted), and that of other paths is gray.

You can interactively select a node by using dropdowns in jupyter notebook.

We have two technical contributions to the field of visualization using Sankey diagrams.

One is to extend the layer number:
- Ordinary Sankey diagrams can only visualize paths between 2 layers.
- pathSankey can only visualize paths between 3 layers.
- We can visualize the comparison of paths between two layers before and after (up to 5 layers).

The other is to create a notebook that can interact with users. We integrate several functions of ipywidgets into floweaver.

## Requirements

### in this repository (using pip or conda)
- floweaver (==2.0.0a5)
- ipysankeywidget (==0.2.5)

### in floweaver-path repository (using docker)
- docker (installs two libraries: floweaver, ipysankeywidget)

### in both repositories
- input file (`*.csv, *.pickle or *.xlsx` should be put in `data` directory)


## Structure
```
├── README.md
├── data
│   └── template.csv
└── template_before_separation.ipynb
```