import Foundation

struct Product: Identifiable, Codable {
    let id: UUID
    let barcode: String
    let name: String
    let category: String
    let imageURL: URL?
    let ingredientsText: String
    let packagingText: String
    let rawKeywords: [String]

    init(
        barcode: String,
        name: String,
        category: String,
        imageURL: URL?,
        ingredientsText: String,
        packagingText: String,
        rawKeywords: [String]
    ) {
        self.id = UUID()
        self.barcode = barcode
        self.name = name
        self.category = category
        self.imageURL = imageURL
        self.ingredientsText = ingredientsText
        self.packagingText = packagingText
        self.rawKeywords = rawKeywords
    }
}
