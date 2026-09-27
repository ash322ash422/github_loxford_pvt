======================================================================
NODE LABELS
======================================================================

Group
Properties:
  • id
  • name
Examples:
  • DataClub
  • team

Organization
Properties:
  • id
  • name
Examples:
  • TechHub
  • TechAssociation

Person
Properties:
  • id
  • name
Examples:
  • Charlie
  • Diana
  • Alice

Platform
Properties:
  • id
  • name
Examples:
  • GitHub
  • Behance
  • LinkedIn

Product
Properties:
  • id
  • name
Examples:
  • ChatApp


======================================================================
RELATIONSHIPS
======================================================================
(Person)-[:CEO_OF]->(Organization)
(Person)-[:CO_ORGANIZES_WITH]->(Person)
(Organization)-[:DEVELOPED]->(Product)
(Person)-[:FOLLOWS]->(Person)
(Person)-[:INTERACTS_WITH]->(Person)
(Organization)-[:MAINTAINS_PROFILE_ON]->(Platform)
(Person)-[:MANAGES]->(Organization)
(Person)-[:MANAGES]->(Person)
(Person)-[:MARRIED_TO]->(Person)
(Person)-[:MEMBER_OF]->(Organization)
(Person)-[:MEMBER_OF]->(Group)
(Person)-[:ORGANIZES]->(Group)
(Person)-[:SHARES_OFFICE_WITH]->(Person)
(Person)-[:USES_PLATFORM]->(Platform)
(Organization)-[:USES_PLATFORM]->(Platform)
(Person)-[:VIEWS_POSTS]->(Person)
(Person)-[:WORKS_AT]->(Organization)
(Person)-[:WORKS_ON]->(Product)