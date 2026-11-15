// docs/mtpc.schema.json, which vite.config.ts puts in the runtime at build time.
declare module "virtual:mtpc-schema" {
  const schema: unknown;
  export default schema;
}
