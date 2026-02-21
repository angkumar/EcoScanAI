import Foundation
import Combine

final class OpenFoodFactsService {
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func fetchProduct(barcode: String) -> AnyPublisher<Product, Error> {
        let trimmed = barcode.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty,
              let url = URL(string: "https://world.openfoodfacts.org/api/v2/product/\(trimmed).json") else {
            return Fail(error: URLError(.badURL)).eraseToAnyPublisher()
        }

        return session.dataTaskPublisher(for: url)
            .map(\.data)
            .decode(type: OpenFoodFactsResponse.self, decoder: JSONDecoder())
            .tryMap { response in
                guard response.status == 1, let apiProduct = response.product else {
                    throw OpenFoodFactsError.notFound
                }
                return apiProduct.toProduct(barcode: trimmed)
            }
            .receive(on: DispatchQueue.main)
            .eraseToAnyPublisher()
    }
}

enum OpenFoodFactsError: LocalizedError {
    case notFound

    var errorDescription: String? {
        switch self {
        case .notFound:
            return "Product not found in Open Food Facts."
        }
    }
}

private struct OpenFoodFactsResponse: Decodable {
    let status: Int
    let product: OpenFoodFactsProduct?
}

private struct OpenFoodFactsProduct: Decodable {
    let productName: String?
    let productNameEn: String?
    let imageURL: String?
    let categories: String?
    let categoriesTags: [String]?
    let labelsTags: [String]?
    let packaging: String?
    let packagingTags: [String]?
    let ingredientsText: String?
    let novaGroup: Int?

    enum CodingKeys: String, CodingKey {
        case productName = "product_name"
        case productNameEn = "product_name_en"
        case imageURL = "image_url"
        case categories
        case categoriesTags = "categories_tags"
        case labelsTags = "labels_tags"
        case packaging
        case packagingTags = "packaging_tags"
        case ingredientsText = "ingredients_text"
        case novaGroup = "nova_group"
    }

    func toProduct(barcode: String) -> Product {
        let categoryText = categories ?? categoriesTags?.joined(separator: ", ") ?? "Uncategorized"
        let packagingText = [packaging ?? "", packagingTags?.joined(separator: " ") ?? ""].joined(separator: " ")
        let keywords = [
            categoriesTags?.joined(separator: " ") ?? "",
            labelsTags?.joined(separator: " ") ?? "",
            packagingTags?.joined(separator: " ") ?? "",
            ingredientsText ?? "",
            productName ?? "",
            productNameEn ?? "",
            String(novaGroup ?? 0)
        ]

        return Product(
            barcode: barcode,
            name: productName?.isEmpty == false ? (productName ?? "Unknown Product") : (productNameEn ?? "Unknown Product"),
            category: categoryText,
            imageURL: URL(string: imageURL ?? ""),
            ingredientsText: ingredientsText ?? "",
            packagingText: packagingText,
            rawKeywords: keywords
        )
    }
}
