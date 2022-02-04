class MultiSearch:
    
    def __init__(self, dic):
        self.list_of_merged_dicts = list()

        flag = 0
        hep_dict = dict()
        arxiv_dict = dict()

        hep_keys = list()
        arxiv_keys = list()

        temp_arx_key = ''
        temp_hep_key = ''

        general_dict = dict()

        #generate new dicts for lowering future time complexity
        if dic["HEP"] is not None:
            self.HEP = dic["HEP"]
            for d in self.HEP.list_of_dicts:
                temp_hep_key = d["ID"]
                if temp_hep_key == None:
                    temp_hep_key = d["DOI"]
                hep_dict[temp_hep_key] = d
                hep_keys.append(temp_hep_key)

        if dic["ARXIV"] is not None:   
            self.ARXIV = dic["ARXIV"]
            for d in self.ARXIV.list_of_dicts:
                temp_arx_key = d["ID"]
                if temp_arx_key == None:
                    temp_arx_key = d["DOI"]
                arxiv_dict[temp_arx_key] = d
                arxiv_keys.append(temp_arx_key)
            
        #merge
        for k in arxiv_keys:
            if arxiv_dict[k]["DOI"] is None:
                DOI = hep_dict[k]["DOI"]
                
            else:
                DOI = arxiv_dict[k]["DOI"]
            
            if arxiv_dict[k]["Journal"] is None:
                Journal = hep_dict[k]["Journal"]
                
            else:
                Journal = arxiv_dict[k]["Journal"]



            if hep_dict.get(k,None) == None:
                citations = "No data from HEP"
                flag = 1
            else:
               citations =  hep_dict[k]["Citations"]

            general_dict = {
                "Authors" : arxiv_dict[k]['Authors'],
                "Date_Published" : arxiv_dict[k]['Date_Published'],
                "Last_Update" : arxiv_dict[k]['Last_Update'],
                "Title": arxiv_dict[k]['Title'],
                "ID": arxiv_dict[k]["ID"],
                "DOI": DOI,
                "Journal": Journal,
                "Citations": citations,
                "Num_Of_Authors": arxiv_dict[k]["Num_Of_Authors"]
            }

            self.list_of_merged_dicts.append(general_dict)

            #pop parsed entry
            if flag == 1:
                flag == 0
            else:
                hep_keys.remove(k)
                
            arxiv_dict.pop(k)
        
        for k in hep_keys:
            general_dict = {
                "Authors" : hep_dict[k]['Authors'],
                "Date_Published" : hep_dict[k]['Date_Published'],
                "Last_Update" : None,
                "Title": hep_dict[k]['Title'],
                "ID": hep_dict[k]["ID"],
                "DOI": hep_dict[k]["DOI"],
                "Journal": hep_dict[k]["Journal"],
                "Citations": hep_dict[k]["Citations"],
                "Num_Of_Authors": hep_dict[k]["Num_Of_Authors"]
            }
            self.list_of_merged_dicts.append(general_dict)

    def write(self, filename):
        items = []
        with open(filename, 'w') as f:
            for dic in self.list_of_merged_dicts:
                items = dic.items()
                for el in items:
                    if el[0] == 'Authors':
                        f.write(str(el[0] + ": \n "))
                        for x in el[1]:
                            f.write(str(x+" ,"))
                        f.write('\n\n')
                    else:
                        f.write(str(el[0]) + ": \n" + str(el[1]) + '\n\n')
                f.write('\n')
    
        