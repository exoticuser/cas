const { fetchHome, parseNumber } = require("../lib/castle");

module.exports = async (req, res) => {
  if (req.method !== "GET") {
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }
  const page = parseNumber(req.query.page, 1, { min: 1 });
  const size = parseNumber(req.query.size, 17, { min: 1, max: 50 });
  const secB64 = req.query.sec_b64 || null;

  try {
    const payload = await fetchHome(secB64, page, size);
    res.status(200).json(payload);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
};
