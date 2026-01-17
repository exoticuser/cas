const { fetchSecurityKey } = require("../lib/castle");

module.exports = async (req, res) => {
  if (req.method !== "GET") {
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }
  try {
    const securityKey = await fetchSecurityKey();
    res.status(200).json({ securityKey });
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
};
