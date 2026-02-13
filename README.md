# An unofficial command-line client for ControlMap

## At a glance

[ControlMap](https://www.scalepad.com/controlmap/) is SaaS that helps companies to organize their compliance documents
and processes. It's widely used to manage ISO-27001 certification.

During the introduction of ISO-27001 at `dimedis GmbH` we discovered that ControlMap and LLMS doesn't play well together.
Because ControlMap is entirely browser-based without any documented API we couldn't instruct an LLM to carry out tasks.
However, many tasks could be done perfectly by AI such as
- discuss approaches
- gap analysis
- document reviews
- consistency checking
- resuming documents
- spell checking

The main problem is, that LLMS cannot read what's inside ControlMap.

While there are some export functions they are too limited to allow efficient work with LLMS. On the other hand the 
underlying API beneath the uiser interface is easy to reverse engineer. It follows RESTful patterns so exporting
data in a way LLMS can read them with ease is doable. That's why we created this command-line client for automated
data export.

## Features

With `ctrlmap-cli` you can mirror data and documents from ControlMap to a folder on your disk using machine and 
human-readable data formats such as Markdown, JSON and YAML. You can export

- Policies
- Governance
- Procedures
- Risk Register

## Usage

`ctrlmap-cli` is written in Python and distributed as a single-file zip-app. Python 3.9 or newer is required.

- Download a release to anywhere you like e.g. `/usr/local/bin`.
- Open ControlMap in your browser with Dev-Tools open. Open the network tab of the dev tools and click on "Policies".
  Grab your API base URL and your bearer token.
- Go to an empty folder and make it the folder where ControlMap documents are mirrored to.
  Your API URL of ControlMap is required. E.g. `https://api.eu.ctrlmap.com`
  ```bash
  ctrlmap-cli --init https://<CONTROLMAP-API-URL>/
  ```
  You will be asked interactively for the bearer token. Your input will not be displayed on the console.
  This step will create the file `.ctrlmap-cli.ini` and the basic folder structure.
  ```text
  .
  ├── .ctrlmap-cli.ini
  ├── governance
  ├── policies
  ├── procedures
  └── risks
  ```
- Now you can copy all or individual parts by using:
  - `ctrlmap-cli --copy-all`
  - `ctrlmap-cli --copy-gov`
  - `ctrlmap-cli --copy-pols`
  - `ctrlmap-cli --copy-pros`
  - `ctrlmap-cli --copy-risks`