import Foundation

struct ScanAnalysis: Identifiable {
    let id = UUID()
    let product: Product
    let impactScore: ImpactScore
    let reason: String
    let disposalInstruction: DisposalInstruction
    let suggestedAlternative: String

    var shareSummary: String {
        """
        EcoScan AI Result
        Product: \(product.name)
        Impact: \(impactScore.rawValue) (\(impactScore.label))
        CO2 Estimate: \(String(format: "%.1f", impactScore.co2Estimate)) kg
        Disposal: \(disposalInstruction.disposalType.rawValue)
        Suggestion: \(suggestedAlternative)
        """
    }
}
