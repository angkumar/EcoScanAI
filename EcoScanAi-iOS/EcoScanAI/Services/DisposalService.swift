import Foundation

final class DisposalService {
    private struct Rule {
        let matches: [String]
        let disposalType: DisposalType
        let detail: String
    }

    private let cityRules: [City: [Rule]] = [
        .sanFrancisco: [
            Rule(matches: ["plastic", "pet", "hdpe", "glass", "aluminum", "metal can"], disposalType: .recycle, detail: "Rinse and place in blue bin."),
            Rule(matches: ["food scrap", "compostable", "paper", "cardboard"], disposalType: .compost, detail: "Place in green compost bin if food-soiled or compostable."),
            Rule(matches: ["battery", "electronics", "aerosol"], disposalType: .specialDropOff, detail: "Use SF hazardous waste or e-waste drop-off."),
            Rule(matches: ["film", "wrapper", "styrofoam"], disposalType: .trash, detail: "Place in black landfill bin.")
        ],
        .chicago: [
            Rule(matches: ["plastic", "glass", "aluminum", "metal can", "carton"], disposalType: .recycle, detail: "Rinse and place in Chicago Blue Cart."),
            Rule(matches: ["food scrap", "compostable"], disposalType: .compost, detail: "Use a local compost program or approved drop-off."),
            Rule(matches: ["battery", "electronics", "paint", "light bulb"], disposalType: .specialDropOff, detail: "Take to a City of Chicago HHW/electronics site."),
            Rule(matches: ["film", "wrapper", "foam"], disposalType: .trash, detail: "Dispose in trash if not accepted by local recycling.")
        ]
    ]

    func instruction(for city: City, packagingText: String, category: String) -> DisposalInstruction {
        let normalized = "\(packagingText) \(category)".lowercased()
        let rules = cityRules[city] ?? []

        for rule in rules where rule.matches.contains(where: normalized.contains) {
            return DisposalInstruction(city: city, disposalType: rule.disposalType, detail: rule.detail)
        }

        return DisposalInstruction(
            city: city,
            disposalType: .trash,
            detail: "Material unclear. Check your city's sorting guide for this package."
        )
    }
}
