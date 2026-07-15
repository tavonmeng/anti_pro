export const DELIVERABLE_MAX_FILE_SIZE = 200 * 1024 * 1024
export const DELIVERABLE_MAX_FILE_SIZE_MB = 200

export const DELIVERABLE_ACCEPTED_EXTENSIONS = [
  '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg',
  '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.key', '.txt',
  '.psd', '.ai', '.eps', '.sketch', '.fig',
  '.fbx', '.obj', '.max', '.blend', '.c4d',
  '.zip', '.rar', '.7z',
] as const

export const DELIVERABLE_ACCEPT = DELIVERABLE_ACCEPTED_EXTENSIONS.join(',')

export const isDeliverableFileSizeAllowed = (size: number) =>
  size <= DELIVERABLE_MAX_FILE_SIZE
