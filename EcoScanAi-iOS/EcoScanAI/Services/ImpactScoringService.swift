import Foundation

struct ImpactScoringResult {
    let score: ImpactScore
    let reason: String
}

final class ImpactScoringService {
    func score(product: Product) -> ImpactScoringResult {
        let blob = ([product.name, product.category, product.ingredientsText, product.packagingText] + product.rawKeywords)
            .joined(separator: " ")
            .lowercased()

        if blob.contains("beef") || blob.contains("meat") {
            return ImpactScoringResult(score: .red, reason: "Meat-heavy category detected, which usually has a higher footprint.")
        }

        if blob.contains("nova 4") || blob.contains("packaged") || blob.contains("ultra-processed") || blob.contains("chips") {
            return ImpactScoringResult(score: .yellow, reason: "Likely ultra-processed packaged food.")
        }

        if blob.contains("plant") || blob.contains("vegan") || blob.contains("vegetarian") || blob.contains("plant-based") {
            return ImpactScoringResult(score: .green, reason: "Plant-based indicators found.")
        }

        if blob.contains("bulk") || blob.contains("recyclable") || blob.contains("paper") {
            return ImpactScoringResult(score: .green, reason: "Lower packaging impact indicators found.")
        }

        return ImpactScoringResult(score: .yellow, reason: "Insufficient data, assigned medium impact.")
    }

    func suggestion(for score: ImpactScore, productName: String) -> String {
        switch score {
        case .red:
            return "Try a plant-based alternative to \(productName) and pick low-packaging options."
        case .yellow:
            return "Look for a less-processed or refill-style option for \(productName)."
        case .green:
            return "Great pick. Keep prioritizing local and minimal-packaging choices."
        }
    }
}
