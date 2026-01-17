const { fetchDetails } = require("../lib/castle");

module.exports = async (req, res) => {
  if (req.method !== "GET") {
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }
  const movieId = req.query.movie_id;
  if (!movieId) {
    res.status(400).json({ error: "movie_id is required" });
    return;
  }
  const secB64 = req.query.sec_b64 || null;

  try {
    const payload = await fetchDetails(secB64, movieId);
    res.status(200).json(payload);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
};
