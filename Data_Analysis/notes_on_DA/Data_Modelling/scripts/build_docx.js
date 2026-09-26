const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, AlignmentType, ImageRun, TableOfContents,
  PageBreak, LevelFormat, convertInchesToTwip, VerticalAlign, Header, Footer,
  PageNumber, NumberFormat, ExternalHyperlink
} = require("docx");

const IMG = "/tmp/dm_workshop/images";
const PAGE_W = 12240, PAGE_H = 15840; // US Letter
const MARGIN = 1080; // 0.75in
const USABLE = PAGE_W - MARGIN * 2; // 10080 DXA

// ---------- palette ----------
const NAVY = "1F3B57";
const TEAL = "2E7D6B";
const LITE = "EDF3F7";
const ACCENT = "C0392B";
const GREY = "607080";

// ---------- small helpers ----------
function H1(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 160 } });
}
function H2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 } });
}
function H3(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 100 } });
}
function P(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 160, line: 276 },
    children: [new TextRun({ text, ...opts })],
  });
}
function Rich(runs, opts = {}) {
  return new Paragraph({ spacing: { after: 160, line: 276 }, ...opts, children: runs });
}
function Bold(text) { return new TextRun({ text, bold: true }); }
function It(text) { return new TextRun({ text, italics: true }); }

function Bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { after: 90 },
    children: [new TextRun(text)],
  });
}
function BulletRich(runs, level = 0) {
  return new Paragraph({ numbering: { reference: "bullets", level }, spacing: { after: 90 }, children: runs });
}
function NumberedItem(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "numbers", level },
    spacing: { after: 90 },
    children: [new TextRun(text)],
  });
}

function calloutBox(title, text, color = TEAL) {
  return new Table({
    width: { size: USABLE, type: WidthType.DXA },
    columnWidths: [USABLE],
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: USABLE, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, fill: LITE },
            margins: { top: 140, bottom: 140, left: 180, right: 180 },
            borders: {
              top: { style: BorderStyle.SINGLE, size: 16, color },
              bottom: { style: BorderStyle.SINGLE, size: 4, color: "CFD8DC" },
              left: { style: BorderStyle.SINGLE, size: 16, color },
              right: { style: BorderStyle.SINGLE, size: 4, color: "CFD8DC" },
            },
            children: [
              new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: title, bold: true, color })] }),
              new Paragraph({ spacing: { after: 0 }, children: [new TextRun({ text })] }),
            ],
          }),
        ],
      }),
    ],
  });
}

function spacer(h = 160) {
  return new Paragraph({ spacing: { after: h }, children: [] });
}

// Data table builder: headers[], rows[][], colWidths[] (sum must equal USABLE or a given total)
function dataTable(headers, rows, colWidths, opts = {}) {
  const total = colWidths.reduce((a, b) => a + b, 0);
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => new TableCell({
      width: { size: colWidths[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: opts.headerFill || NAVY },
      verticalAlign: VerticalAlign.CENTER,
      margins: { top: 90, bottom: 90, left: 110, right: 110 },
      children: [new Paragraph({
        alignment: AlignmentType.LEFT,
        children: [new TextRun({ text: h, bold: true, color: "FFFFFF", size: 20 })],
      })],
    })),
  });
  const bodyRows = rows.map((r) => new TableRow({
    children: r.map((cell, i) => new TableCell({
      width: { size: colWidths[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: "FFFFFF" },
      verticalAlign: VerticalAlign.CENTER,
      margins: { top: 80, bottom: 80, left: 110, right: 110 },
      children: [new Paragraph({ children: [new TextRun({ text: String(cell), size: 20 })] })],
    })),
  }));
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headerRow, ...bodyRows],
  });
}

function image(path, widthPx, ratio, caption) {
  const heightPx = Math.round(widthPx / ratio);
  const data = fs.readFileSync(path);
  const children = [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 120, after: caption ? 60 : 200 },
      children: [new ImageRun({ data, type: "png", transformation: { width: widthPx, height: heightPx } })],
    }),
  ];
  if (caption) {
    children.push(new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 220 },
      children: [new TextRun({ text: caption, italics: true, size: 18, color: GREY })],
    }));
  }
  return children;
}

// ---------- image aspect ratios (width/height), measured from the PNGs ----------
const RATIO = {
  star: 1.494, snowflake: 1.391, scd1: 1.987, scd2: 2.143, scd3: 2.045,
  denorm: 2.126, norm: 1.959, grain: 1.896, keys: 2.909,
};
const FULL_W = 620; // px at 96dpi ≈ 6.45in, fits inside the 7in usable page width

// =====================================================================
// DOCUMENT BODY
// =====================================================================
const body = [];

// ---- Title page ----
body.push(
  new Paragraph({ spacing: { before: 1400, after: 0 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "DATA MODELING", bold: true, size: 60, color: NAVY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 40 },
    children: [new TextRun({ text: "for Analytics & Data Warehousing", size: 32, color: TEAL, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 260, after: 0 },
    children: [new TextRun({ text: "A 1-Hour Teaching Session", size: 24, italics: true, color: GREY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 40, after: 0 },
    children: [new TextRun({ text: "Star & Snowflake Schemas  ·  Fact & Dimension Tables  ·  Slowly Changing Dimensions", size: 20, color: GREY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 10, after: 0 },
    children: [new TextRun({ text: "Granularity & Surrogate Keys  ·  Normalization vs. Denormalization", size: 20, color: GREY })] }),
  spacer(500),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
    children: [new TextRun({ text: "Worked example used throughout: \"BrightMart\" retail sales dataset", size: 20, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Theory  +  Visual Diagrams  +  Hands-on Practical Exercises", size: 20 })] }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Table of contents (static — renders correctly without a manual "update fields" step) ----
function tocLine(num, title, page) {
  return new Paragraph({
    spacing: { after: 140 },
    tabStops: [{ type: "right", position: USABLE, leader: "dot" }],
    children: [
      new TextRun({ text: `${num}  ${title}`, size: 22 }),
      new TextRun({ text: `\t${page}`, size: 22 }),
    ],
  });
}
body.push(
  H1("Contents"),
  tocLine("1.", "Why Data Modeling Matters", 4),
  tocLine("2.", "Fact and Dimension Tables", 4),
  tocLine("3.", "Star Schema vs. Snowflake Schema", 6),
  tocLine("4.", "Granularity and Surrogate Keys", 8),
  tocLine("5.", "Slowly Changing Dimensions (SCD)", 10),
  tocLine("6.", "Normalization vs. Denormalization", 13),
  tocLine("7.", "Practical Exercises", 15),
  tocLine("8.", "Answer Key (Instructor Reference)", 16),
  tocLine("9.", "One-Page Cheat Sheet", 18),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Agenda ----
body.push(
  H1("Session Agenda (60 minutes)"),
  P("Suggested pacing — adjust based on audience familiarity with SQL and databases."),
  dataTable(
    ["Time", "Topic", "Format"],
    [
      ["0:00 – 0:05", "Why data modeling matters", "Discussion"],
      ["0:05 – 0:18", "Fact & dimension tables, Star vs Snowflake schema", "Theory + diagrams"],
      ["0:18 – 0:28", "Granularity & surrogate keys", "Theory + diagram"],
      ["0:28 – 0:48", "Slowly Changing Dimensions — Types 1, 2, 3", "Theory + worked examples"],
      ["0:48 – 0:56", "Normalization vs denormalization", "Theory + diagrams"],
      ["0:56 – 1:00", "Wrap-up, cheat sheet, hand out exercises", "Recap + Q&A"],
    ],
    [2000, 5700, 2380],
  ),
  spacer(200),
  calloutBox("Instructor tip", "The four practical exercises at the end (Section 8) are designed to be assigned as take-home work if class time runs out — each maps directly to one theory section above."),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Section: Why data modeling ----
body.push(
  H1("1. Why Data Modeling Matters"),
  P("A data model is the blueprint for how data is organized, stored, and related. In analytics, a good model means analysts write simple queries and get consistent numbers; a bad model means every report calculates \"revenue\" a little differently."),
  H3("What good data modeling gives you"),
  Bullet("Query performance — fewer, simpler JOINs for the queries the business runs most often."),
  Bullet("A shared business vocabulary — \"customer\", \"order\", \"region\" mean the same thing everywhere."),
  Bullet("Predictable structure — BI tools (Power BI, Tableau, Looker) can auto-detect facts and dimensions."),
  Bullet("Controlled history — you decide, deliberately, what changes are tracked over time and what isn't."),
  P("The techniques in this session — dimensional modeling, grain, surrogate keys, SCDs, and normalization trade-offs — are the standard toolkit for designing analytical (OLAP) data models, as popularized by Ralph Kimball's dimensional modeling methodology."),
);

// ---- Section 2: Fact & Dimension tables ----
body.push(
  H1("2. Fact and Dimension Tables"),
  P("Dimensional modeling organizes data into two kinds of tables:"),
  H2("Fact tables"),
  P("Store the measurements/events of the business — things that happened. Rows are typically numeric, additive, and high in volume."),
  Bullet("Contain measures: quantities that can be summed, averaged, counted (e.g. sales_amount, quantity)."),
  Bullet("Contain foreign keys to every relevant dimension (date_key, store_key, product_key, customer_key)."),
  Bullet("Grow continuously — one row per event, so millions/billions of rows are normal."),
  Bullet("Are narrow (few columns) but very tall (many rows)."),
  H2("Dimension tables"),
  P("Store the descriptive context that explains the facts — the who/what/where/when. Rows are textual, describe attributes, and are used to filter, group, and label reports."),
  Bullet("Contain descriptive attributes (product_name, category, city, loyalty_tier)."),
  Bullet("Are wide (many columns) but comparatively short (few thousand to few million rows)."),
  Bullet("Change slowly over time — this is exactly the problem Slowly Changing Dimensions (Section 6) solves."),
  Bullet("Are joined to the fact table via keys — ideally surrogate keys (Section 5)."),
  spacer(100),
  dataTable(
    ["Aspect", "Fact Table", "Dimension Table"],
    [
      ["Contains", "Measures / metrics", "Descriptive attributes"],
      ["Shape", "Narrow & tall (few cols, many rows)", "Wide & short (many cols, fewer rows)"],
      ["Changes", "Append-only (new events)", "Attributes updated over time"],
      ["Example", "FACT_SALES", "DIM_CUSTOMER, DIM_PRODUCT, DIM_STORE"],
      ["Used for", "\"How much / how many\"", "\"By whom / where / when / what kind\""],
    ],
    [2200, 4000, 3880],
  ),
  H2("Practical: the BrightMart sample dataset"),
  P("We'll use one consistent scenario throughout this session: BrightMart, a small electronics retailer with three stores. This is the fact table at line-item grain, and its four dimensions."),
);

// FACT_SALES table (real data)
body.push(
  H3("FACT_SALES"),
  dataTable(
    ["sales_key", "date_key", "store_key", "product_key", "customer_key", "qty", "unit_price", "sales_amount"],
    [
      ["1", "20260601", "1", "1", "501", "2", "2499", "4998"],
      ["2", "20260601", "1", "3", "501", "1", "1299", "1299"],
      ["3", "20260602", "2", "4", "502", "1", "13999", "13999"],
      ["4", "20260606", "3", "1", "502", "3", "2499", "7497"],
      ["5", "20260615", "1", "2", "501", "1", "2799", "2799"],
      ["6", "20260701", "2", "3", "502", "2", "1299", "2598"],
    ],
    [1080, 1080, 1080, 1140, 1260, 700, 1180, 1560],
  ),
  spacer(160),
  H3("DIM_DATE, DIM_STORE, DIM_PRODUCT, DIM_CUSTOMER (star-schema / flattened versions)"),
  dataTable(
    ["date_key", "full_date", "day_name", "month", "quarter", "year"],
    [
      ["20260601", "2026-06-01", "Monday", "June", "Q2", "2026"],
      ["20260602", "2026-06-02", "Tuesday", "June", "Q2", "2026"],
      ["20260606", "2026-06-06", "Saturday", "June", "Q2", "2026"],
    ],
    [1600, 1900, 1700, 1700, 1400, 1780],
  ),
  spacer(140),
  dataTable(
    ["store_key", "store_id", "store_name", "city", "region", "country"],
    [
      ["1", "ST-101", "BrightMart Andheri", "Mumbai", "West", "India"],
      ["2", "ST-102", "BrightMart Koramangala", "Bengaluru", "South", "India"],
      ["3", "ST-103", "BrightMart Salt Lake", "Kolkata", "East", "India"],
    ],
    [1200, 1300, 3000, 1600, 1300, 1680],
  ),
  spacer(140),
  dataTable(
    ["product_key", "sku", "product_name", "category", "subcategory", "brand"],
    [
      ["1", "SKU-5001", "AeroBuds Pro", "Electronics", "Audio", "Aero"],
      ["3", "SKU-6010", "VoltCharge 65W", "Electronics", "Power", "Volt"],
      ["4", "SKU-7020", "PixelView 24 Monitor", "Electronics", "Computing", "Pixel"],
    ],
    [1350, 1450, 2900, 1650, 1500, 1230],
  ),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Section 3: Star vs Snowflake ----
body.push(
  H1("3. Star Schema vs. Snowflake Schema"),
  P("These are the two classic ways to arrange a fact table and its dimensions."),
  H2("Star schema"),
  P("Each dimension is a single, flattened (denormalized) table directly connected to the fact table. Every attribute of a dimension — however hierarchical it conceptually is (city → region → country) — lives in one wide row."),
  ...image(`${IMG}/star_schema.png`, FULL_W, RATIO.star, "Figure 1 — Star schema: FACT_SALES surrounded by four flattened dimension tables."),
  H2("Snowflake schema"),
  P("One or more dimensions are further normalized into sub-dimensions. Here, DIM_STORE is split into City → Region → Country, and DIM_PRODUCT into Subcategory → Category — removing repeated text but requiring extra JOINs to reach it."),
  ...image(`${IMG}/snowflake_schema.png`, FULL_W, RATIO.snowflake, "Figure 2 — Snowflake schema: the same fact table, but Store and Product dimensions are normalized into chains of smaller tables."),
  H2("Choosing between them"),
  dataTable(
    ["Aspect", "Star Schema", "Snowflake Schema"],
    [
      ["Dimension structure", "Denormalized (flat, wide)", "Normalized into sub-dimensions"],
      ["Joins per query", "Fewer (1 hop to any attribute)", "More (multi-hop through sub-tables)"],
      ["Query simplicity", "Simpler for BI tools & analysts", "More complex SQL"],
      ["Storage", "Some redundant text (e.g. \"India\" repeated)", "Less redundancy, smaller dimension tables"],
      ["Typical use", "Most data warehouses / BI layers", "Very large, deeply hierarchical dimensions"],
    ],
    [2200, 4000, 3880],
  ),
  spacer(120),
  calloutBox("Rule of thumb", "Default to a star schema. Snowflake only where a dimension is huge and its hierarchy is reused independently elsewhere — the JOIN cost usually isn't worth it just to save disk space.", TEAL),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Section 4: Grain & surrogate keys ----
body.push(
  H1("4. Granularity and Surrogate Keys"),
  H2("Granularity (\"grain\")"),
  P("The grain of a fact table is the precise definition of what a single row represents. It must be decided before choosing measures or dimensions — everything else follows from it."),
  ...image(`${IMG}/granularity.png`, FULL_W, RATIO.grain, "Figure 3 — The same underlying sales data at three different grains."),
  Bullet("Finer grain (e.g. one row per product line) = maximum flexibility, more rows, more storage."),
  Bullet("Coarser grain (e.g. one row per store per day) = smaller table, faster simple reports, but detail is lost forever."),
  BulletRich([Bold("Golden rule: "), new TextRun("declare the grain in one sentence before modeling — e.g. “one row per product sold, per transaction line.”")]),
  H2("Surrogate keys"),
  P("A surrogate key is a system-generated identifier (usually a simple auto-incrementing integer) used as the primary key of a dimension table, instead of the business's own \"natural\" key (SKU, email, national ID, etc.)."),
  ...image(`${IMG}/surrogate_vs_natural_key.png`, FULL_W, RATIO.keys, "Figure 4 — Natural key vs. surrogate key."),
  Bullet("Surrogate keys are immune to source-system changes (a SKU gets renamed, an email changes)."),
  Bullet("They are required to implement SCD Type 2 — the same natural key (SKU-5001) can then have two rows (surrogate keys 1 and 2) representing two versions over time."),
  Bullet("Integer joins are faster than string / composite-key joins."),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Section 5: SCD ----
body.push(
  H1("5. Slowly Changing Dimensions (SCD)"),
  P("Dimension attributes are not permanent — a customer moves city, a product gets recategorized, a store gets renamed. An SCD strategy is the deliberate policy for how a dimension table reacts when a source attribute changes."),
  P("Worked scenario used below: customer Arjun Mehta (CUST-02) relocates from Pune to Mumbai on 2026-07-10."),
  H2("Type 1 — Overwrite (no history)"),
  P("The changed attribute is simply updated in place. The old value is gone."),
  ...image(`${IMG}/scd_type1.png`, FULL_W, RATIO.scd1, "Figure 5 — SCD Type 1: the row is overwritten; 'Pune' is lost."),
  Bullet("Use when: the old value has no analytical value, or correcting bad data (e.g. fixing a typo)."),
  Bullet("Downside: any report that used the old value historically will silently change — you cannot answer “what did sales by city look like last quarter” correctly."),

  H2("Type 2 — New row (full history)"),
  P("The existing row is “closed” (its end_date is set and is_current flips to 'N'), and a brand new row is inserted with a new surrogate key holding the new value."),
  ...image(`${IMG}/scd_type2.png`, FULL_W, RATIO.scd2, "Figure 6 — SCD Type 2: old row is expired, a new row with a new surrogate key is inserted."),
  Bullet("Requires a surrogate key (natural key CUST-02 now maps to two rows: 502 and 901)."),
  Bullet("Typical tracking columns: start_date, end_date (or valid_from / valid_to), and is_current (or a version_number)."),
  Bullet("Fact rows loaded before the change keep pointing at the old surrogate key, so historical reports stay accurate — this is the main reason Type 2 is the default choice in most warehouses."),
  Bullet("Downside: dimension table grows over time; queries needing “current view only” must filter is_current = 'Y'."),

  H2("Type 3 — New column (limited history)"),
  P("The row itself is not duplicated. Instead, a new column stores the immediately-previous value alongside the current one."),
  ...image(`${IMG}/scd_type3.png`, FULL_W, RATIO.scd3, "Figure 7 — SCD Type 3: the row stays the same; 'previous_city' captures one step of history."),
  Bullet("Use when you only ever need to compare “current vs. prior” (e.g. “previous sales region” for a one-time reorg)."),
  Bullet("Downside: only keeps one (or a fixed number of) prior values — a second change overwrites the “previous” column too."),

  H2("Choosing a type"),
  dataTable(
    ["", "Type 1: Overwrite", "Type 2: New Row", "Type 3: New Column"],
    [
      ["History kept", "None", "Full", "One prior value"],
      ["New surrogate key?", "No", "Yes, per change", "No"],
      ["Table grows?", "No", "Yes (new row per change)", "No"],
      ["Query complexity", "Simplest", "Needs is_current / date filter", "Simple, but limited"],
      ["Typical use case", "Fixing errors, low-value attributes", "Customer address, product category, price tier", "Sales territory realignment, one-off comparisons"],
    ],
    [2080, 2600, 2900, 2500],
  ),
  spacer(120),
  calloutBox("Good to know", "Types 0, 4, and 6 also exist: Type 0 = attribute never changes (e.g. date of birth); Type 4 = current values stay in the dimension, history moves to a separate historical table; Type 6 = a hybrid of 1+2+3. Types 1, 2, and 3 cover the vast majority of real-world cases and are the ones worth mastering first.", ACCENT),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Section 6: Normalization vs denormalization ----
body.push(
  H1("6. Normalization vs. Denormalization"),
  H2("Normalization"),
  P("Normalization organizes data to remove redundancy: every fact is stored exactly once, and tables are split so that non-key attributes depend only on the whole primary key (this is, informally, what 3rd Normal Form / 3NF aims for). It is the default design approach for transactional (OLTP) systems — the systems that run the business day-to-day."),
  H2("Denormalization"),
  P("Denormalization deliberately re-introduces redundancy — merging tables or repeating attributes — to make reads faster and queries simpler. This is exactly what a star schema's flattened dimension tables do."),
  ...image(`${IMG}/denormalized_orders.png`, FULL_W, RATIO.denorm, "Figure 8 — Denormalized: customer details repeat on every order row."),
  ...image(`${IMG}/normalized_orders.png`, FULL_W, RATIO.norm, "Figure 9 — Normalized (3NF): customer details stored once, referenced by customer_id."),
  dataTable(
    ["Aspect", "Normalized", "Denormalized"],
    [
      ["Redundancy", "Minimal — each fact stored once", "Deliberate — attributes repeated"],
      ["Update anomalies", "Avoided", "Possible if not carefully managed"],
      ["Read (query) speed", "Slower — needs JOINs", "Faster — fewer/no JOINs"],
      ["Write consistency", "Easy — one place to update", "Harder — must update every copy"],
      ["Typical system", "OLTP (transactional apps)", "OLAP / data warehouse dimensions"],
    ],
    [1900, 4000, 4180],
  ),
  spacer(120),
  calloutBox("How this ties back to Section 3", "A star schema's dimension tables are intentionally denormalized (fast reads for BI tools). A snowflake schema pushes those same dimensions back toward normalization (less redundancy, more JOINs). Neither is “right” — it's a trade-off between read speed and redundancy, chosen based on query patterns.", TEAL),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Section 7: Exercises ----
body.push(
  H1("7. Practical Exercises"),
  P("Use the BrightMart dataset from Section 2 (or your own) for all exercises below. Suggested: do Exercise 1 together in class; assign the rest as homework. An answer key follows in Section 8."),

  H2("Exercise 1 — Identify the grain"),
  P("BrightMart's warehouse team gives you a raw export with these columns: transaction_id, transaction_line_no, store_id, product_sku, customer_id, sale_date, quantity, line_amount."),
  NumberedItem("In one sentence, state the grain of a fact table built directly from this export."),
  NumberedItem("If your finance team only ever asks “total revenue by store by month,” would you model the fact table at this grain, or coarser? Justify your answer."),
  NumberedItem("Name one question you could answer at the fine grain that you could NOT answer if you pre-aggregated to store-by-month."),

  H2("Exercise 2 — Design a star schema"),
  P("Scenario: a hospital wants to analyze appointments. Each appointment has: a patient, a doctor, a clinic location, an appointment date/time, a duration in minutes, and a billed amount."),
  NumberedItem("List the fact table and its measures."),
  NumberedItem("List each dimension table and 3–4 attributes it should hold."),
  NumberedItem("Draw (on paper or in a tool) the star schema, showing foreign keys from the fact table to each dimension."),
  NumberedItem("Would you snowflake the “clinic location” dimension into City → Region? Under what condition would that be worth it?"),

  H2("Exercise 3 — Apply an SCD"),
  P("BrightMart's DIM_PRODUCT has: product_key 4, sku SKU-7020, product_name “PixelView 24 Monitor”, category “Electronics”, brand “Pixel”. On 2026-08-01, the product is reclassified from category “Electronics” to a new category “Computing Accessories”."),
  NumberedItem("Write out the resulting row(s) if you apply SCD Type 1."),
  NumberedItem("Write out the resulting row(s) if you apply SCD Type 2 (include start_date / end_date / is_current, and a new surrogate key)."),
  NumberedItem("Write out the resulting row if you apply SCD Type 3 (include a previous_category column)."),
  NumberedItem("Which type would you recommend for a “product category” attribute at a retail chain, and why?"),

  H2("Exercise 4 — Normalize a flat table"),
  P("You are given one wide CSV export with columns: order_id, customer_name, customer_phone, customer_city, store_name, store_city, product_name, product_category, quantity, price."),
  NumberedItem("Identify which columns are repeated/redundant across rows for the same customer, store, or product."),
  NumberedItem("Split this into a normalized set of tables (aim for something close to 3NF): list each table and its columns, including primary/foreign keys."),
  NumberedItem("Name one update anomaly that the original flat table was at risk of, that your normalized design fixes."),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Section 8: Answer key ----
body.push(
  H1("8. Answer Key (Instructor Reference)"),

  H2("Exercise 1 — Grain"),
  Bullet("Grain: “One row per product line within a transaction” (finest available grain in the export)."),
  Bullet("For “total revenue by store by month” only, a coarser grain would technically answer today's question — but modeling at the fine grain is still recommended, since you can always aggregate up in a query. If you model coarse and a new requirement appears (e.g. “top products per store”), you'd need to reload history from source, which may no longer be available."),
  Bullet("Fine grain lets you answer: “what is the average number of items per transaction,” “which products are commonly bought together,” or “revenue per SKU” — all impossible once rows are pre-summed to store-month."),

  H2("Exercise 2 — Hospital star schema"),
  Bullet("FACT_APPOINTMENTS — measures: duration_minutes, billed_amount, count (1 per appointment). FKs: date_key, patient_key, doctor_key, clinic_key."),
  Bullet("DIM_PATIENT: patient_key, patient_id, name, date_of_birth, gender, insurance_plan."),
  Bullet("DIM_DOCTOR: doctor_key, doctor_id, name, specialization, years_experience."),
  Bullet("DIM_CLINIC: clinic_key, clinic_name, city, region."),
  Bullet("DIM_DATE: date_key, full_date, day_name, month, quarter, year."),
  Bullet("Snowflaking clinic into City → Region is worth it only if the hospital network is large (hundreds of clinics) and City/Region are reused as their own reporting dimension elsewhere — otherwise keep it flat (star)."),

  H2("Exercise 3 — SCD on product category"),
  Bullet("Type 1: product_key 4 row is updated in place — category becomes “Computing Accessories”; the fact that it was ever “Electronics” is lost."),
  Bullet("Type 2: existing row (key 4) gets end_date = 2026-07-31, is_current = 'N'. A new row is inserted, e.g. key 40, sku SKU-7020, category “Computing Accessories”, start_date = 2026-08-01, end_date = 9999-12-31, is_current = 'Y'."),
  Bullet("Type 3: row (key 4) keeps its key; category becomes “Computing Accessories” and a new column previous_category = “Electronics” is populated."),
  Bullet("Recommended: Type 2. Category changes affect how historical revenue rolls up by category — you want old fact rows to still report under “Electronics” for periods before the reclassification, and new rows under “Computing Accessories.”"),

  H2("Exercise 4 — Normalizing the flat export"),
  Bullet("Redundant columns: customer_name/phone/city repeat for every order by the same customer; store_name/city repeat for every order at that store; product_name/category repeat for every order of that product."),
  BulletRich([Bold("ORDERS"), new TextRun("(order_id PK, customer_id FK, store_id FK, product_id FK, quantity, price)")]),
  BulletRich([Bold("CUSTOMERS"), new TextRun("(customer_id PK, customer_name, customer_phone, customer_city)")]),
  BulletRich([Bold("STORES"), new TextRun("(store_id PK, store_name, store_city)")]),
  BulletRich([Bold("PRODUCTS"), new TextRun("(product_id PK, product_name, product_category)")]),
  Bullet("Update anomaly fixed: previously, if a customer's phone number changed, every historical order row for that customer needed updating — miss one, and the customer now has two different phone numbers on file. Now it's stored once in CUSTOMERS."),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---- Section 9: Cheat sheet ----
body.push(
  H1("9. One-Page Cheat Sheet"),
  dataTable(
    ["Concept", "In one line"],
    [
      ["Fact table", "Numeric events/measures + FKs to dimensions. Tall & narrow."],
      ["Dimension table", "Descriptive attributes for filtering/grouping. Wide & shorter."],
      ["Star schema", "Fact + flattened (denormalized) dimensions. Fewer JOINs."],
      ["Snowflake schema", "Fact + normalized, multi-level dimensions. More JOINs, less redundancy."],
      ["Grain", "What one fact row represents — decide this first, before anything else."],
      ["Surrogate key", "System-generated PK for a dimension; stable, fast, enables SCD Type 2."],
      ["SCD Type 1", "Overwrite. No history."],
      ["SCD Type 2", "New row + new surrogate key. Full history."],
      ["SCD Type 3", "New column for prior value. One step of history."],
      ["Normalization", "Remove redundancy; each fact stored once. Standard for OLTP."],
      ["Denormalization", "Add redundancy back for read speed. Standard for OLAP dimensions."],
    ],
    [2600, 7480],
  ),
);

// =====================================================================
// Assemble document
// =====================================================================
const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 260 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 900, hanging: 260 } } } },
        ],
      },
      {
        reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 260 } } } },
        ],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 22 } },
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: NAVY, font: "Calibri" },
        paragraph: { spacing: { before: 320, after: 160 }, border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: NAVY, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: TEAL, font: "Calibri" },
        paragraph: { spacing: { before: 240, after: 120 } } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, color: "455A64", font: "Calibri" },
        paragraph: { spacing: { before: 200, after: 100 } } },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: PAGE_W, height: PAGE_H },
          margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
        },
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "Data Modeling — 1-Hour Session", size: 16, color: GREY })],
          })],
        }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Page ", size: 16, color: GREY }),
              new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GREY }),
              new TextRun({ text: " of ", size: 16, color: GREY }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, color: GREY }),
            ],
          })],
        }),
      },
      children: body,
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("/tmp/dm_workshop/Data_Modeling_1Hour_Session.docx", buf);
  console.log("written");
});
