const test = require("node:test");
const assert = require("node:assert/strict");
const { normalizePickedFile } = require("./uploadFile.cjs");

test("normalizes Expo document picker asset shape", () => {
  assert.deepEqual(
    normalizePickedFile({
      assets: [{ uri: "file:///tmp/invoice.pdf", name: "invoice.pdf", mimeType: "application/pdf", size: 1234 }],
    }),
    {
      uri: "file:///tmp/invoice.pdf",
      name: "invoice.pdf",
      type: "application/pdf",
      size: 1234,
    },
  );
});

test("normalizes legacy single-asset picker result", () => {
  assert.deepEqual(
    normalizePickedFile({ type: "success", uri: "file:///tmp/photo.jpg", fileName: "photo.jpg" }, "image/jpeg"),
    {
      uri: "file:///tmp/photo.jpg",
      name: "photo.jpg",
      type: "image/jpeg",
      size: null,
    },
  );
});

test("returns null for canceled picker results", () => {
  assert.equal(normalizePickedFile({ canceled: true }), null);
  assert.equal(normalizePickedFile({ type: "cancel" }), null);
});

test("rejects picker results without a usable URI", () => {
  assert.throws(() => normalizePickedFile({ assets: [] }), /readable URI/);
});

test("does not mistake a generic asset type for a MIME type", () => {
  assert.equal(
    normalizePickedFile({ uri: "file:///tmp/photo.jpg", type: "image" }, "image/jpeg").type,
    "image/jpeg",
  );
});

test("infers a useful MIME type from legacy picker filename", () => {
  assert.equal(
    normalizePickedFile({ type: "success", uri: "file:///tmp/invoice.pdf", name: "invoice.pdf" }).type,
    "application/pdf",
  );
});
