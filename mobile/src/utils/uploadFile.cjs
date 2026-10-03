const MIME_BY_EXTENSION = {
  pdf: "application/pdf",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  gif: "image/gif",
  webp: "image/webp",
  txt: "text/plain",
  csv: "text/csv",
  doc: "application/msword",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  xls: "application/vnd.ms-excel",
  xlsx: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
};

function normalizePickedFile(result, fallbackType = "application/octet-stream") {
  if (!result || result.canceled === true || result.cancelled === true || result.type === "cancel") {
    return null;
  }

  const asset = Array.isArray(result.assets) ? result.assets[0] : result;
  if (!asset || typeof asset.uri !== "string" || !asset.uri.trim()) {
    throw new Error("The selected file did not include a readable URI.");
  }

  const name = asset.name || asset.fileName || "upload";
  const candidateType = asset.mimeType || asset.type;
  const declaredMime =
    typeof candidateType === "string" && candidateType.includes("/")
      ? candidateType
      : null;
  const extension = name.includes(".") ? name.split(".").pop().toLowerCase() : "";
  const mimeType = declaredMime || MIME_BY_EXTENSION[extension] || fallbackType;

  return {
    uri: asset.uri,
    name,
    type: mimeType,
    size: Number.isFinite(asset.size) ? asset.size : null,
  };
}

module.exports = { normalizePickedFile };
