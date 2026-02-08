export default [
  // ESM build
  {
    input: "src/index.js",
    output: {
      file: "dist/floweaver-executor.esm.js",
      format: "es",
    },
  },
  // UMD build (for script tags)
  {
    input: "src/index.js",
    output: {
      file: "dist/floweaver-executor.umd.js",
      format: "umd",
      name: "floweaver",
    },
  },
];
