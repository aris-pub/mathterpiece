// The validator that vite.config.ts writes from docs/mtpc.schema.json at build time.
declare module "virtual:mtpc-schema" {
  export interface SchemaError {
    instancePath: string;
    keyword: string;
    params: Record<string, unknown>;
  }
  const validate: ((data: unknown) => boolean) & { errors?: SchemaError[] | null };
  export default validate;
}
