import React, { useState, useEffect } from 'react';
import { getDefaultDiscordAvatar } from '../utils/discord';

/**
 * Reusable UserAvatar component with automatic fallback to Discord's official default avatar.
 */
const UserAvatar = ({
  src,
  userId,
  alt = '',
  size = 40,
  style = {},
  className = '',
  onClick,
  title,
  ...props
}) => {
  const defaultAvatar = getDefaultDiscordAvatar(userId);
  const [imgSrc, setImgSrc] = useState(src || defaultAvatar);
  const [hasError, setHasError] = useState(!src);

  useEffect(() => {
    setImgSrc(src || defaultAvatar);
    setHasError(!src);
  }, [src, userId]);

  const handleError = () => {
    if (!hasError) {
      setHasError(true);
      setImgSrc(defaultAvatar);
    }
  };

  const dim = typeof size === 'number' ? `${size}px` : size;

  return (
    <img
      src={imgSrc}
      alt={hasError ? '' : alt}
      onError={handleError}
      style={{
        width: dim,
        height: dim,
        minWidth: dim,
        minHeight: dim,
        borderRadius: '50%',
        objectFit: 'cover',
        display: 'inline-block',
        ...style
      }}
      className={className}
      onClick={onClick}
      title={title}
      {...props}
    />
  );
};

export default UserAvatar;
