import { Avatar } from "antd";

import { avatarColours, initials } from "../lib/avatar";

/** A person's initials in a circle. Decoration: their name is always written beside it. */
export function PersonAvatar({ name, size = 32 }: { name: string; size?: number }) {
  const [background, color] = avatarColours(name);
  return (
    <Avatar
      aria-hidden
      size={size}
      style={{ background, color, flex: "none", fontSize: size * 0.4, fontWeight: 600 }}
    >
      {initials(name)}
    </Avatar>
  );
}
