/**
 * Discord Utility Functions
 */

/**
 * Calculates the official Discord default avatar URL based on the user ID.
 * Discord formula: (userId >> 22) % 6
 * @param {string|number} userId - Discord user snowflake ID
 * @returns {string} CDN URL for the default avatar (0.png to 5.png)
 */
export const getDefaultDiscordAvatar = (userId) => {
  try {
    if (!userId) return 'https://cdn.discordapp.com/embed/avatars/0.png';
    const cleanId = String(userId).trim();
    if (/^\d+$/.test(cleanId)) {
      const index = Number((BigInt(cleanId) >> 22n) % 6n);
      return `https://cdn.discordapp.com/embed/avatars/${Math.abs(index)}.png`;
    }
  } catch (e) {
    // BigInt or parsing fallback
  }
  return 'https://cdn.discordapp.com/embed/avatars/0.png';
};
