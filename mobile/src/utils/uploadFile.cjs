function normalizePickedFile(result, fallbackType = "application/octet-stream") {
  if (!result || result.canceled === true || result.cancelled === true || result.type === "cancel") {
    return null;
  }

  const asset = Array.isArray(result.assets) ? result.assets[0] : result;
  if (!asset || typeof asset.uri !== "string" || !asset.uri.trim()) {
    throw new Error("The selected file did not include a readable URI.");
  }

  const candidateType = asset.mimeType || asset.type;
  const mimeType =
    typeof candidateType === "string" && candidateType.includes("/")
      ? candidateType
      : fallbackType;

  return {
    uri: asset.uri,
    name: asset.name || asset.fileName || "upload",
    type: mimeType,
    size: Number.isFinite(asset.size) ? asset.size : null,
  };
}

module.exports = { normalizePickedFile };
