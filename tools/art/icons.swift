// icons.swift: the Ridgeway site icons from the app icon (CoreGraphics only).
//
//   swift icons.swift APPICON_1024.png OUT_DIR
//
// Writes:
//   icon-1024.png          the app icon as shipped (opaque square, no alpha); round it with CSS
//   apple-touch-icon.png   180 x 180, opaque square (iOS applies its own mask)
//   favicon-32.png         32 x 32, rounded-square mask with alpha (browser tabs)
//   icon-256.png           256 x 256, rounded-square mask with alpha (page header / footer use)
//
// favicon.svg is hand-written from the same geometry as docs/design/icon/render_icon.swift.

import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count == 3 else { fatalError("usage: swift icons.swift APPICON_1024.png OUT_DIR") }
let srcURL = URL(fileURLWithPath: args[1])
let outDir = URL(fileURLWithPath: args[2], isDirectory: true)
let sRGB = CGColorSpace(name: CGColorSpace.sRGB)!

guard let src = CGImageSourceCreateWithURL(srcURL as CFURL, nil),
      let icon = CGImageSourceCreateImageAtIndex(src, 0, nil) else { fatalError("cannot read \(srcURL.path)") }

func write(_ image: CGImage, _ name: String) {
    let url = outDir.appendingPathComponent(name)
    let dest = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, image, nil)
    guard CGImageDestinationFinalize(dest) else { fatalError("could not write \(url.path)") }
    print("wrote \(name) (\(image.width)x\(image.height))")
}

/// Continuous-corner-ish rounded square (iOS icon proportions: radius ~22.4% of the side).
func roundedSquare(_ s: CGFloat) -> CGPath {
    CGPath(roundedRect: CGRect(x: 0, y: 0, width: s, height: s),
           cornerWidth: s * 0.2237, cornerHeight: s * 0.2237, transform: nil)
}

func render(_ side: Int, rounded: Bool) -> CGImage {
    let info = rounded ? CGImageAlphaInfo.premultipliedLast.rawValue : CGImageAlphaInfo.noneSkipLast.rawValue
    let ctx = CGContext(data: nil, width: side, height: side, bitsPerComponent: 8, bytesPerRow: 0,
                        space: sRGB, bitmapInfo: info)!
    ctx.interpolationQuality = .high
    if rounded {
        ctx.addPath(roundedSquare(CGFloat(side)))
        ctx.clip()
    }
    // Downsample in steps of at most 2x for a clean result at small sizes.
    var current = icon
    while current.width / 2 >= side * 2 {
        let w = current.width / 2
        let c = CGContext(data: nil, width: w, height: w, bitsPerComponent: 8, bytesPerRow: 0,
                          space: sRGB, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
        c.interpolationQuality = .high
        c.draw(current, in: CGRect(x: 0, y: 0, width: w, height: w))
        current = c.makeImage()!
    }
    ctx.draw(current, in: CGRect(x: 0, y: 0, width: side, height: side))
    return ctx.makeImage()!
}

write(icon, "icon-1024.png")
write(render(180, rounded: false), "apple-touch-icon.png")
write(render(32, rounded: true), "favicon-32.png")
write(render(256, rounded: true), "icon-256.png")
