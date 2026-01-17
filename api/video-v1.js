const { fetchVideoV1 } = require("../lib/castle");

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.status(405).json({ error: "Method Not Allowed" });
    return;
  }
  const {
    movie_id: movieId,
    episode_id: episodeId,
    language_id: languageId,
    resolution,
  } = req.body || {};
  if (!movieId || !episodeId || !languageId) {
    res.status(400).json({
      error: "movie_id, episode_id, and language_id are required",
    });
    return;
  }
  const secB64 = req.query.sec_b64 || null;

  try {
    const payload = await fetchVideoV1(secB64, {
      movieId,
      episodeId,
      languageId,
      resolution: resolution ?? 2,
    });
    res.status(200).json(payload);
  } catch (error) {
    res.status(502).json({ error: error.message });
  }
};
