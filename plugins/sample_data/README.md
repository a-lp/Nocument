# Sample data

Example plugin package of Nocument: it creates sample contents (a heading, paragraphs, a bar chart and a sales
table) without any external service, so you can try plugins and use the package as a starting point for your own.

## What it creates

| Content   | Parameters                                   |
| --------- | -------------------------------------------- |
| Heading   | title, optional date, level                  |
| Paragraph | number of paragraphs, optional opening line  |
| Image     | number of bars, color, width in cm           |
| Table     | number of products, total row, caption       |

In the Builder, in *Add new content* and in the Compiler the contents come from the **From plugin** section of the
content form: choose *Sample data*, fill in its fields and click **Load data**.

## Interface

The plugin page (**Plugins → Installed plugins → Sample data**) opens its own interface, a small report
playground: choose how many products, the chart color and width, and generate the table and the chart together, with
a preview as they will look in a document.

The interface saves in this browser (not on the server):

- the last settings used;
- named **presets**, to load them again later;
- how many reports were generated.

## Files

- `plugin.py`: the `SampleDataPlugin` class (`IPlugin`), with its parameters and a `compile_<type>` method for each
  content type. The chart is a PNG drawn with the standard library only.
- `ui.svelte`: the interface (Svelte 5). It uses `api.compile` to create the contents, `components.ContentSheet` to
  preview them, `storage` for the presets and the theme's CSS variables (`--accent`, `--surface`, ...) for the colors.
- `README.md`: this guide.
