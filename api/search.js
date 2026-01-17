const { fetchSearch, parseNumber } = require("../lib/castle");

module.exports = async (req, res) => {
  if (req.method !== "GET") {
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }
  const keyword = req.query.keyword;
  if (!keyword) {
    res.status(400).json({ error: "keyword is required" });
    return;
  }
  const page = parseNumber(req.query.page, 1, { min: 1 });
  const size = parseNumber(req.query.size, 30, { min: 1, max: 50 });
  const secB64 = req.query.sec_b64 || null;

  try {
    const payload = await fetchSearch(secB64, keyword, page, size);
    res.status(200).json(payload);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
};
