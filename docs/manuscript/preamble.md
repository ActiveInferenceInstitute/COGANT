# LaTeX Preamble

This file contains LaTeX packages and commands that are automatically injected into the document compilation process when this manuscript is rendered through the template rendering pipeline.

> **Infrastructure note**: Parsed by `infrastructure/rendering/latex_utils.py` and combined with configuration from `infrastructure/rendering/pdf_renderer.py` before Pandoc runs.

```latex
% Core mathematics
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{amsthm}

% Document layout
\usepackage{geometry}
\usepackage{float}
\usepackage{graphicx}

% Tables
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}

% Algorithm typesetting
\usepackage[ruled,vlined,linesnumbered]{algorithm2e}

% Code listings
\usepackage{listings}

% Typography and formatting
\usepackage{microtype}
\usepackage{xcolor}
\usepackage[binary-units]{siunitx}

% Cross-references and citations
% Internal and citation links: red; URLs: blue---reduces reliance on hue alone for distinction.
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=red,
    citecolor=red,
    filecolor=red,
    urlcolor=blue,
    menucolor=red,
    runcolor=red,
    anchorcolor=red
}
\usepackage[capitalise,noabbrev]{cleveref}
\usepackage{natbib}
```
