// ABOUTME: Draws Semilayered Slicer's placeholder artwork and writes every image file the application ships it as.
// ABOUTME: Run on macOS from the repository root: swift semilayered/artwork/generate.swift

import AppKit
import CoreText
import ImageIO

let outputRoot = "semilayered/artwork/tree"
let fontFile = "resources/fonts/NanumGothic-Bold.ttf"

let slate = "#1F2933"
let teal = "#2DD4BF"
let paper = "#F5F7FA"
let grayTile = "#4A4A4A"
let grayBar = "#C8C8C8"

/// A filled outline. Coordinates run from the top left, y downwards, as in SVG.
struct Shape {
    let path: CGPath
    let fill: String
}

struct Drawing {
    let width: CGFloat
    let height: CGFloat
    let shapes: [Shape]
}

enum MarkStyle {
    case colour, gray, barsOnly
}

// MARK: The mark and the name

/// The mark: a rounded square holding three layers, the top one half printed.
func mark(x: CGFloat, y: CGFloat, side: CGFloat, style: MarkStyle = .colour) -> [Shape] {
    var shapes: [Shape] = []
    if style != .barsOnly {
        let tile = CGRect(x: x, y: y, width: side, height: side)
        let corner = side * 0.22
        shapes.append(Shape(path: CGPath(roundedRect: tile, cornerWidth: corner, cornerHeight: corner, transform: nil),
                            fill: style == .gray ? grayTile : slate))
    }
    let barHeight = side * 0.12
    let gap = side * 0.09
    let fullWidth = side * 0.56
    let left = x + side * 0.22
    let top = y + (side - (3 * barHeight + 2 * gap)) / 2
    for row in 0..<3 {
        let bar = CGRect(x: left, y: top + CGFloat(row) * (barHeight + gap),
                         width: row == 0 ? fullWidth / 2 : fullWidth, height: barHeight)
        shapes.append(Shape(path: CGPath(roundedRect: bar, cornerWidth: barHeight / 2, cornerHeight: barHeight / 2, transform: nil),
                            fill: style == .gray ? grayBar : teal))
    }
    return shapes
}

let fontDescriptors = CTFontManagerCreateFontDescriptorsFromURL(URL(fileURLWithPath: fontFile) as CFURL) as? [CTFontDescriptor] ?? []
guard let fontDescriptor = fontDescriptors.first else {
    FileHandle.standardError.write("cannot read \(fontFile); run this from the repository root\n".data(using: .utf8)!)
    exit(1)
}

func glyphs(_ string: String, size: CGFloat) -> (font: CTFont, glyphs: [CGGlyph], advances: [CGSize]) {
    let font = CTFontCreateWithFontDescriptor(fontDescriptor, size, nil)
    let characters = Array(string.utf16)
    var found = [CGGlyph](repeating: 0, count: characters.count)
    CTFontGetGlyphsForCharacters(font, characters, &found, characters.count)
    var advances = [CGSize](repeating: .zero, count: found.count)
    CTFontGetAdvancesForGlyphs(font, .horizontal, found, &advances, found.count)
    return (font, found, advances)
}

func textWidth(_ string: String, size: CGFloat) -> CGFloat {
    glyphs(string, size: size).advances.reduce(0) { $0 + $1.width }
}

/// The largest type size, up to a limit, at which the string is no wider than the given width.
func sizeToFit(_ string: String, width: CGFloat, limit: CGFloat) -> CGFloat {
    min(limit, width / textWidth(string, size: 1))
}

/// The string as outlines, so the image needs no font where it is shown.
func text(_ string: String, x: CGFloat, baseline: CGFloat, size: CGFloat, fill: String) -> Shape {
    let set = glyphs(string, size: size)
    let outline = CGMutablePath()
    var pen = x
    for (glyph, advance) in zip(set.glyphs, set.advances) {
        // Glyph outlines have y upwards; this drawing has y downwards.
        var place = CGAffineTransform(a: 1, b: 0, c: 0, d: -1, tx: pen, ty: baseline)
        if let glyphOutline = CTFontCreatePathForGlyph(set.font, glyph, &place) {
            outline.addPath(glyphOutline)
        }
        pen += advance.width
    }
    return Shape(path: outline, fill: fill)
}

// MARK: Layouts

/// The mark alone on a square canvas.
func markAlone(canvas: CGFloat, inset: CGFloat = 0.04, style: MarkStyle = .colour) -> Drawing {
    Drawing(width: canvas, height: canvas,
            shapes: mark(x: canvas * inset, y: canvas * inset, side: canvas * (1 - 2 * inset), style: style))
}

/// The mark centred on a canvas of any shape.
func markCentred(width: CGFloat, height: CGFloat) -> Drawing {
    let side = min(width, height) * 0.8
    return Drawing(width: width, height: height, shapes: mark(x: (width - side) / 2, y: (height - side) / 2, side: side))
}

/// The mark with the name in two lines to its right. `onDark` picks the colour of the name.
func markBesideName(width: CGFloat, height: CGFloat, onDark: Bool) -> Drawing {
    let margin = height * 0.15
    let side = height - 2 * margin
    let textLeft = margin + side + margin
    let size = sizeToFit("Semilayered", width: width - textLeft - margin, limit: height * 0.34)
    let ink = onDark ? paper : slate
    var shapes = mark(x: margin, y: margin, side: side)
    shapes.append(text("Semilayered", x: textLeft, baseline: height * 0.47, size: size, fill: ink))
    shapes.append(text("Slicer", x: textLeft, baseline: height * 0.47 + size * 1.15, size: size, fill: ink))
    return Drawing(width: width, height: height, shapes: shapes)
}

/// The mark with the name in two lines beneath it, centred.
func markAboveName(canvas: CGFloat, onDark: Bool) -> Drawing {
    let side = canvas * 0.42
    let size = sizeToFit("Semilayered", width: canvas * 0.62, limit: canvas * 0.12)
    let ink = onDark ? paper : slate
    var shapes = mark(x: (canvas - side) / 2, y: canvas * 0.14, side: side)
    for (line, string) in ["Semilayered", "Slicer"].enumerated() {
        let baseline = canvas * 0.14 + side + size * 1.5 + CGFloat(line) * size * 1.2
        shapes.append(text(string, x: (canvas - textWidth(string, size: size)) / 2, baseline: baseline, size: size, fill: ink))
    }
    return Drawing(width: canvas, height: canvas, shapes: shapes)
}

// MARK: File formats

func colour(_ hex: String) -> CGColor {
    let value = UInt32(hex.dropFirst(), radix: 16)!
    return CGColor(srgbRed: CGFloat((value >> 16) & 0xFF) / 255, green: CGFloat((value >> 8) & 0xFF) / 255,
                   blue: CGFloat(value & 0xFF) / 255, alpha: 1)
}

func svg(_ drawing: Drawing, viewBox: String, width: String, height: String) -> Data {
    func number(_ value: CGFloat) -> String { String(format: "%.2f", Double(value)) }
    var body = ""
    for shape in drawing.shapes {
        var data = ""
        shape.path.applyWithBlock { element in
            let points = element.pointee.points
            switch element.pointee.type {
            case .moveToPoint: data += "M\(number(points[0].x)) \(number(points[0].y))"
            case .addLineToPoint: data += "L\(number(points[0].x)) \(number(points[0].y))"
            case .addQuadCurveToPoint:
                data += "Q\(number(points[0].x)) \(number(points[0].y)) \(number(points[1].x)) \(number(points[1].y))"
            case .addCurveToPoint:
                data += "C\(number(points[0].x)) \(number(points[0].y)) \(number(points[1].x)) \(number(points[1].y)) \(number(points[2].x)) \(number(points[2].y))"
            case .closeSubpath: data += "Z"
            @unknown default: break
            }
        }
        body += "  <path fill=\"\(shape.fill)\" d=\"\(data)\"/>\n"
    }
    let document = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"\(width)\" height=\"\(height)\" viewBox=\"\(viewBox)\">\n\(body)</svg>\n"
    return document.data(using: .utf8)!
}

/// The drawing as pixels: 8-bit blue, green, red, alpha with alpha premultiplied, top row first.
func pixels(_ drawing: Drawing, wide: Int, high: Int) -> (context: CGContext, bytes: [UInt8]) {
    let context = CGContext(data: nil, width: wide, height: high, bitsPerComponent: 8, bytesPerRow: wide * 4,
                            space: CGColorSpace(name: CGColorSpace.sRGB)!,
                            bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)!
    context.translateBy(x: 0, y: CGFloat(high))
    context.scaleBy(x: CGFloat(wide) / drawing.width, y: -CGFloat(high) / drawing.height)
    for shape in drawing.shapes {
        context.addPath(shape.path)
        context.setFillColor(colour(shape.fill))
        context.fillPath()
    }
    let buffer = UnsafeBufferPointer(start: context.data!.assumingMemoryBound(to: UInt8.self), count: wide * high * 4)
    return (context, Array(buffer))
}

func png(_ drawing: Drawing, side: Int) -> Data {
    let image = pixels(drawing, wide: side, high: side).context.makeImage()!
    let data = NSMutableData()
    let destination = CGImageDestinationCreateWithData(data, "public.png" as CFString, 1, nil)!
    CGImageDestinationAddImage(destination, image, nil)
    CGImageDestinationFinalize(destination)
    return data as Data
}

func littleEndian<T: FixedWidthInteger>(_ value: T) -> Data {
    withUnsafeBytes(of: value.littleEndian) { Data($0) }
}

/// One icon as the uncompressed bitmap ICO files use for sizes below 256: 32-bit pixels, bottom row first, then a mask.
func icoBitmap(_ drawing: Drawing, side: Int) -> Data {
    let premultiplied = pixels(drawing, wide: side, high: side).bytes
    var data = Data()
    data += littleEndian(UInt32(40)) + littleEndian(Int32(side)) + littleEndian(Int32(side * 2))
    data += littleEndian(UInt16(1)) + littleEndian(UInt16(32)) + littleEndian(UInt32(0)) + littleEndian(UInt32(side * side * 4))
    data += Data(count: 16)
    for row in stride(from: side - 1, through: 0, by: -1) {
        for column in 0..<side {
            let at = (row * side + column) * 4
            let alpha = Int(premultiplied[at + 3])
            for channel in 0..<3 {
                data.append(alpha == 0 ? 0 : UInt8(min(255, Int(premultiplied[at + channel]) * 255 / alpha)))
            }
            data.append(UInt8(alpha))
        }
    }
    // The mask is unused when pixels carry alpha, but the format still wants it: one bit per pixel, rows padded to 32 bits.
    data += Data(count: ((side + 31) / 32) * 4 * side)
    return data
}

/// An ICO file holding the drawing at each size. As upstream's icons do, 256 is stored as PNG and the rest as bitmaps.
func ico(_ drawing: Drawing, sides: [Int]) -> Data {
    let images = sides.map { $0 >= 256 ? png(drawing, side: $0) : icoBitmap(drawing, side: $0) }
    var file = littleEndian(UInt16(0)) + littleEndian(UInt16(1)) + littleEndian(UInt16(sides.count))
    var offset = 6 + 16 * sides.count
    for (side, image) in zip(sides, images) {
        file += Data([UInt8(side >= 256 ? 0 : side), UInt8(side >= 256 ? 0 : side), 0, 0])
        file += littleEndian(UInt16(1)) + littleEndian(UInt16(32)) + littleEndian(UInt32(image.count)) + littleEndian(UInt32(offset))
        offset += image.count
    }
    return images.reduce(file, +)
}

/// An ICNS file holding the drawing at every size macOS asks for, built by the system's iconutil.
func icns(_ drawing: Drawing) -> Data {
    let holder = FileManager.default.temporaryDirectory.appendingPathComponent("semilayered-\(ProcessInfo.processInfo.processIdentifier)")
    let iconset = holder.appendingPathComponent("Icon.iconset")
    try! FileManager.default.createDirectory(at: iconset, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: holder) }
    for points in [16, 32, 128, 256, 512] {
        try! png(drawing, side: points).write(to: iconset.appendingPathComponent("icon_\(points)x\(points).png"))
        try! png(drawing, side: points * 2).write(to: iconset.appendingPathComponent("icon_\(points)x\(points)@2x.png"))
    }
    let output = holder.appendingPathComponent("Icon.icns")
    let iconutil = Process()
    iconutil.executableURL = URL(fileURLWithPath: "/usr/bin/iconutil")
    iconutil.arguments = ["-c", "icns", iconset.path, "-o", output.path]
    try! iconutil.run()
    iconutil.waitUntilExit()
    precondition(iconutil.terminationStatus == 0, "iconutil failed")
    return try! Data(contentsOf: output)
}

// MARK: Every file, at the path of the upstream image it replaces (with the product renamed)

let icon = markAlone(canvas: 1024)
let macIcon = markAlone(canvas: 1024, inset: 0.10)
let grayIcon = markAlone(canvas: 1024, style: .gray)
let barsOnly = markAlone(canvas: 1024, style: .barsOnly)
let images = "resources/images/SemilayeredSlicer"

let files: [(String, Data)] = [
    ("resources/Icon.icns", icns(macIcon)),
    ("\(images)-mac_128px.png", png(macIcon, side: 128)),
    ("\(images)-mac_256px.ico", ico(macIcon, sides: [256])),
    ("\(images).ico", ico(icon, sides: [16, 32, 48, 64, 128, 256])),
    ("\(images).png", png(icon, side: 154)),
    ("\(images).svg", svg(markAlone(canvas: 48), viewBox: "0 0 48 48", width: "64", height: "64")),
    ("\(images)Title.ico", ico(icon, sides: [154])),
    ("\(images)Title.png", png(icon, side: 154)),
    ("\(images)_128px.png", png(icon, side: 128)),
    ("\(images)_154.png", png(icon, side: 154)),
    ("\(images)_154_title.png", png(icon, side: 184)),
    ("\(images)_192px.png", png(icon, side: 192)),
    ("\(images)_192px_grayscale.png", png(grayIcon, side: 192)),
    ("\(images)_192px_transparent.png", png(barsOnly, side: 192)),
    ("\(images)_32px.png", png(icon, side: 32)),
    ("\(images)_64.png", png(icon, side: 64)),
    ("\(images)_about.svg", svg(markBesideName(width: 420, height: 93.75, onDark: false), viewBox: "0 0 420 93.749996", width: "560", height: "125")),
    ("\(images)_about_dark.svg", svg(markBesideName(width: 420, height: 93.75, onDark: true), viewBox: "0 0 420 93.749996", width: "560", height: "125")),
    ("\(images)_gradient.svg", svg(markCentred(width: 768, height: 768), viewBox: "0 0 768 767.999994", width: "1024", height: "1024")),
    ("\(images)_gradient_narrow.svg", svg(markCentred(width: 611.25, height: 768), viewBox: "0 0 611.25 767.999994", width: "815", height: "1024")),
    ("\(images)_gray.svg", svg(markAlone(canvas: 48, style: .gray), viewBox: "0 0 48 48", width: "64", height: "64")),
    ("\(images)_horizontal_dark.svg", svg(markBesideName(width: 214, height: 80, onDark: true), viewBox: "0 0 214 80", width: "214", height: "80")),
    ("\(images)_horizontal_light.svg", svg(markBesideName(width: 214, height: 80, onDark: false), viewBox: "0 0 214 80", width: "214", height: "80")),
    ("resources/images/splash_logo.svg", svg(markAboveName(canvas: 360, onDark: false), viewBox: "0 0 360 359.999987", width: "480", height: "480")),
    ("resources/images/splash_logo_dark.svg", svg(markAboveName(canvas: 360, onDark: true), viewBox: "0 0 360 359.999987", width: "480", height: "480")),
    ("resources/web/image/logo.png", png(icon, side: 154)),
]

for (path, data) in files {
    let url = URL(fileURLWithPath: outputRoot).appendingPathComponent(path)
    try! FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try! data.write(to: url)
}
print("wrote \(files.count) images under \(outputRoot)")
