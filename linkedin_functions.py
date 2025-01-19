from config import *
import json
import re
import requests


def getHeadersFromFirefox(headers):
    headers1 = {}
    for line in headers.split("\n")[1:-1]:
        headers1[line.split(':')[0]] = line[line.find(':')+2:]
    return headers1


def linkedinEncodeURL(str_out):
    str_out = re.sub(r':li:((\w)+)+:', r'%3Ali%3A\1%3A', str_out)
    str_out = str_out.replace('\n', '')

    return str_out


def encodeInner(str_out):
    str_out = str_out.replace(' ', '%20')
    str_out = str_out.replace(':', '%3A')
    str_out = str_out.replace('\n', '')
    str_out = str_out.replace('(', '%28')
    str_out = str_out.replace(')', '%29')
    str_out = str_out.replace(',', '%2C')

    return str_out


def requestFacetDict(text, kind, cookies=cookies, headers=headers, accountId=accountId):
    """
    Query API for all the information needed to encode a single attribute, like its URN and name
    :param text: the attribute whose info is being requested, e.g. "female"
    :param kind: the type of attribute, e.g. "genders"
    :param cookies: the cookies obtained from Firefox
    :param headers: the headers obtained from Firefox
    :param accountId: the accountId associated with the LinkedIn Advertising Campaign
    :return: the dictionary (originally in json format) containing the attribute's information
    """
    # construct query, submit and parse response's json
    query = "https://www.linkedin.com/campaign-manager-api/campaignManagerAdTargetingEntities?query={0}&accountId={1}&facets=List(urn%3Ali%3AadTargetingFacet%3A{2})&q=queryAndMultiFacetTypeahead"""
    query = query.format(text, accountId, kind)

    response = requests.get(query, headers=headers, cookies=cookies)
    parsed = json.loads(response.content)

    # make sure the query has returned something - return dictionary if so, otherwise exit with no return
    try:
        return parsed['elements'][0]
    except:
        return


def encodeFacet(criteria, kind='locations'):
    """
    Encode attribute or attributes' information into single string for final request URL
    :param criteria: the audience attributes - either a list of strings, the attributes in "human-readable" format, or
    a list of dictionaries containing the attributes' API mappings, obtained using the requestFacetDict function
    :param kind: the type of attribute, e.g. "genders"
    :return: the string for that particular type of attribute, which can be used to query the API
    """
    # make sure requested 'kind' is supported
    assert kind in ['locations', 'genders', 'ageRanges', 'degrees', 'fieldsOfStudy', 'seniorities', 'schools', 'industries']

    # return joined criteria if they have already been encoded
    if any('urn:urn' in criterion for criterion in criteria if criterion is not None):
        return ','.join(criteria)

    tc = ""

    # no criteria corresponds to querying all possible attributes of a certain dimensions, e.g. all education levels
    if not criteria:
        return tc
    elif type(criteria) is list:
        # when criteria is the list of attributes, first build a list of the attributes' values in dict format
        if type(criteria[0]) is str:
            new_criteria = []
            for criterion in criteria:
                location_dict = requestFacetDict(criterion, kind)
                if location_dict is not None:
                    new_criteria.append(location_dict)
                else:
                    print(f"URN for '{criterion}' not found")
            # if none of the attributes could be found in the API print warning and return empty string
            if not new_criteria:
                print("The API did not return any results for these parameters")
                return tc
            # replace old text-format criteria with new dict-format ones
            criteria = new_criteria

        # with attributes in dict format, proceed to encoding into final string
        if type(criteria[0]) is dict:
            try:
                for i, criterion in enumerate(criteria):
                    # the API can return incorrect attribute values, e.g. '&' will not work to get counts and should be
                    # replaced with 'and' - it is possible that other such errors exist
                    criterion['name'] = criterion['name'].replace('&', 'and')
                    tc += "(urn:" + encodeInner(criterion['urn'])
                    tc += ",name:" + encodeInner(criterion["name"])
                    tc += ",facetUrn:" + encodeInner(criterion['facetUrn'])
                    tc += ")"
                    if i < len(criteria) - 1:
                        tc += ","
                return tc
            # raise error if dictionaries do not have the expected keys
            except:
                print("The dictionaries in the list do not have the required keys and/or values.")
                assert False
        elif criteria[0] is None:
            return tc
        else:
            print("The function's argument should be a list of strings or a list of correctly formatted dicts.")
            assert False
    else:
        print("The function's argument should be a list of strings or a list of correctly formatted dicts.")
        assert False


def createRequestDataForAudienceCounts(locations,
                                       genders=None, age_groups=None,
                                       degrees=None, fields=None,
                                       seniorities=None,
                                       schools=None, industries=None):
    """
    Combine all attributes into single request string, encoding and requesting facets when necessary
    :param locations: list of audience location(s), must always be specified
    :param genders: list of genders (optional)
    :param age_groups: list of age groups (optional)
    :param degrees: list of degrees/education levels (optional)
    :param fields: list of fields of study (optional)
    :param seniorities: list of job seniorities (optional)
    :param industries: list of company sectors/industries (optional)
    :return: the string that can be used to query the API and get the desired audience count
    """
    if genders is None:
        genders = []
    if age_groups is None:
        age_groups = []
    if degrees is None:
        degrees = []
    if fields is None:
        fields = []
    if seniorities is None:
        seniorities = []
    if schools is None:
        schools = []
    if industries is None:
        industries = []


    tc = """
q=targetingCriteria&cmTargetingCriteria=
(include:
 (and:List
  (
   (or:List
    (
     (facet:
      (urn:urn:li:adTargetingFacet:locations,name:Locations
      ),segments:List
      ( """
    tc += encodeFacet(criteria=locations, kind='locations')
    tc += """   
      )
     )
    )
   ),
   (or:List
    (
     (facet:
      (urn:urn:li:adTargetingFacet:genders,name:Member Gender
      ),segments:List
      ( """
    tc += encodeFacet(criteria=genders, kind='genders')
    tc += """  
      )
     )
    )
   ),
   (or:List
    (
     (facet:
      (urn:urn:li:adTargetingFacet:ageRanges,name:Member Age
      ),segments:List
      ( """
    tc += encodeFacet(criteria=age_groups, kind='ageRanges')
    tc += """
      )
     )
    )
   ),
   (or:List
    (
     (facet:
      (urn:urn:li:adTargetingFacet:degrees,name:Degrees
      ),segments:List
      ( """
    tc += encodeFacet(criteria=degrees, kind='degrees')
    tc += """   
      )
     )
    )
   ),
   (or:List
    (
     (facet:
      (urn:urn:li:adTargetingFacet:fieldsOfStudy,name:Fields of Study
      ),segments:List
      ( """
    tc += encodeFacet(criteria=fields, kind='fieldsOfStudy')
    tc += """   
      )
     )
    )
   ),
   (or:List
    (
     (facet:
      (urn:urn:li:adTargetingFacet:seniorities,name:Job Seniorities
      ),segments:List
      ( """
    tc += encodeFacet(criteria=seniorities, kind='seniorities')
    tc += """   
      )
     )
    )
   ),
   (or:List
    (
     (facet:
      (urn:urn:li:adTargetingFacet:schools,name:Member Schools
      ),segments:List
      ( """
    tc += encodeFacet(criteria=schools, kind='schools')
    tc += """   
      )
     )
    )
   ),
   (or:List
    (
     (facet:
      (urn:urn:li:adTargetingFacet:industries,name:Company Industries
      ),segments:List
      ( """
    tc += encodeFacet(criteria=industries, kind='industries')
    tc += """   
      )
     )
    )
   )
  )
 ),exclude:
 (or:List
  (
  )
 )
)&withValidation=true

"""
    tc = linkedinEncodeURL(tc)
    tc = tc.replace(' ', '')
    return tc


def getAudienceCounts(requestCriteria, headers=testheaders):
    response = requests.post('https://www.linkedin.com/campaign-manager-api/campaignManagerAudienceCounts',
                             headers=getHeadersFromFirefox(headers),
                             data=requestCriteria)
    count = json.loads(response.content)['elements'][0]['count']

    return count
