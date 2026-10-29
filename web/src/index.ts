/** The version of the JSON format this runtime reads. */
export const FORMAT_VERSION = 1;

/** Whether this runtime can play a document. */
export function supports(doc: { mtp?: unknown }): boolean {
  return doc.mtp === FORMAT_VERSION;
}
