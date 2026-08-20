export function imageIsAvailable(image, unavailableImages) {
  return Boolean(image) && !unavailableImages.has(image.src)
}

export function rememberUnavailableImage(unavailableImages, image) {
  unavailableImages.add(image.src)
}
