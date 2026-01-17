const { fetchVideo2 } = require("../lib/castle");

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }
  const { movie_id: movieId, episode_id: episodeId, resolution } = req.body || {};
  if (!movieId || !episodeId) {
    res
      .status(400)
      .json({ error: "movie_id and episode_id are required" });
    return;
  }
  const secB64 = req.query.sec_b64 || null;

  try {
    const payload = await fetchVideo2(secB64, {
      movieId,
      episodeId,
      resolution: resolution ?? 2,
    });
    res.status(200).json(payload);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
};
