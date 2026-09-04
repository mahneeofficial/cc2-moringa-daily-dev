// Save this as client/src/components/AiAvatar.jsx
export default function AiAvatar({ size = 40 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="50" cy="50" r="50" fill="#ea580c" />
      <path d="M50 22L56.5 41.5L76 48L56.5 54.5L50 74L43.5 54.5L24 48L43.5 41.5L50 22Z" fill="white" />
      <circle cx="73" cy="27" r="5" fill="#ffedd5" />
      <circle cx="27" cy="71" r="4" fill="#ffedd5" />
    </svg>
  );
}